from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.contrib import messages

from .models import Prompt, PromptVersion, Action, ContentGenerator
from .forms import PromptVersionForm, ContentGeneratorForm


# ========== ПОДСИСТЕМА PROMPTS ==========

@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    """
    Административный интерфейс для управления типами промптов.
    """
    list_display = (
        'name',
        'get_versions_count',
    )
    list_filter = ()
    search_fields = (
        'name',
        'description',
    )
    readonly_fields = ()
    ordering = ('name',)

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description')
        }),
    )

    def get_versions_count(self, obj):
        """
        Отображает количество версий промпта.
        """
        count = obj.get_versions_count()
        return format_html(
            '<strong>{}</strong>',
            count
        )
    get_versions_count.short_description = 'Версий'


@admin.register(PromptVersion)
class PromptVersionAdmin(admin.ModelAdmin):
    """
    Административный интерфейс для управления версиями промптов.
    Реализует логику "умного версионирования":
    - При изменении prompt_content → создание новой версии
    - При изменении только description → обновление текущей версии
    """
    form = PromptVersionForm
    list_display = (
        'prompt',
        'version_number',
        'description',
        'engineer_name',
        'created_at',
        'get_statistics_display',
    )
    list_filter = (
        'prompt',
        'created_at',
        'engineer_name',
    )
    search_fields = (
        'description',
        'prompt_content',
        'engineer_name',
        'prompt__name',
    )
    readonly_fields = (
        'version_number',
        'created_at',
    )
    ordering = ('-version_number',)

    fieldsets = (
        ('Основная информация', {
            'fields': ('prompt', 'version_number', 'description', 'engineer_name', 'created_at')
        }),
        ('Содержимое промпта', {
            'fields': ('prompt_content',),
            'description': 'При изменении содержимого промпта будет создана новая версия.'
        }),
    )

    class Media:
        js = ('content_generator/js/prompt_version_form.js',)

    def get_form(self, request, obj=None, **kwargs):
        """
        Передает текущего пользователя в форму для автоматического заполнения engineer_name.
        """
        # Извлекаем form_kwargs из kwargs, чтобы не передавать их в modelform_factory
        form_kwargs = kwargs.pop('form_kwargs', {})
        print('form_kwargs', form_kwargs)
        form_kwargs['user'] = request.user
        
        # Получаем класс формы
        form_class = super().get_form(request, obj, **kwargs)
        
        # Создаем обертку, которая будет передавать form_kwargs при создании экземпляра
        class FormWithUser(form_class):
            def __init__(self, *args, **init_kwargs):
                init_kwargs.update(form_kwargs)
                super().__init__(*args, **init_kwargs)
        
        FormWithUser.__name__ = form_class.__name__
        FormWithUser.__module__ = form_class.__module__
        
        return FormWithUser

    def save_model(self, request, obj, form, change):
        """
        Реализует логику "умного версионирования":
        - При создании новой версии: автоматически генерируется номер версии
        - При редактировании существующей версии:
          * Если изменился prompt_content → создается новая версия
          * Если изменилась только description → обновляется текущая версия
        """
        if not change:
            # Создание новой версии
            if not obj.version_number:
                obj.version_number = PromptVersion.get_next_version_number_for_prompt(obj.prompt)
            obj.engineer_name = form.cleaned_data.get('engineer_name', '')
            super().save_model(request, obj, form, change)
            prompt_name = obj.prompt.name if obj.prompt else 'Unknown'
            messages.success(
                request,
                f'Создана новая версия промпта "{prompt_name}" #{obj.version_number}: "{obj.description[:50]}"'
            )
        else:
            # Редактирование существующей версии
            original_obj = PromptVersion.objects.get(pk=obj.pk)
            original_prompt_content = original_obj.prompt_content
            new_prompt_content = form.cleaned_data.get('prompt_content', '')
            
            # Проверяем, изменилось ли содержимое промпта
            if original_prompt_content != new_prompt_content:
                # Создаем новую версию
                new_version_number = PromptVersion.get_next_version_number_for_prompt(obj.prompt)
                new_version = PromptVersion(
                    prompt=obj.prompt,
                    version_number=new_version_number,
                    description=form.cleaned_data.get('description', ''),
                    prompt_content=new_prompt_content,
                    engineer_name=form.cleaned_data.get('engineer_name', ''),
                )
                new_version.save()
                # Не сохраняем оригинальный объект - он остается без изменений
                from django.urls import reverse
                new_version_url = reverse('admin:content_generator_promptversion_change', args=[new_version.pk])
                messages.success(
                    request,
                    format_html(
                        'Создана новая версия промпта #{}. '
                        'Старая версия #{} сохранена без изменений. '
                        '<a href="{}">Перейти к новой версии</a>',
                        new_version_number,
                        original_obj.version_number,
                        new_version_url
                    )
                )
                # Сохраняем ID новой версии в сессии для перенаправления
                request.session['_new_prompt_version_id'] = new_version.pk
            else:
                # Обновляем только описание текущей версии
                obj.description = form.cleaned_data.get('description', '')
                obj.engineer_name = form.cleaned_data.get('engineer_name', '')
                super().save_model(request, obj, form, change)
                messages.info(
                    request,
                    f'Версия промпта #{obj.version_number} обновлена (изменено только описание).'
                )

    def response_change(self, request, obj):
        """
        Перенаправляет на новую версию, если она была создана при изменении содержимого.
        """
        # Проверяем, была ли создана новая версия
        new_version_id = request.session.pop('_new_prompt_version_id', None)
        if new_version_id:
            from django.urls import reverse
            from django.shortcuts import redirect
            return redirect(reverse('admin:content_generator_promptversion_change', args=[new_version_id]))
        
        return super().response_change(request, obj)

    def get_statistics_display(self, obj):
        """
        Отображает статистику использования промпта в списке.
        """
        generated_count = obj.get_generated_content_count()
        reviewed_count = obj.get_reviewed_content_count()
        review_percentage = obj.get_review_percentage()
        avg_rating = obj.get_average_rating()

        stats_parts = [
            f'Сгенерировано: {generated_count}',
            f'Проверено: {reviewed_count} ({review_percentage}%)',
        ]

        if avg_rating is not None:
            stats_parts.append(f'Средний рейтинг: {avg_rating:.2f}')

        return format_html(
            '<div style="font-size: 11px; color: #666;">{}</div>',
            ' | '.join(stats_parts)
        )
    get_statistics_display.short_description = 'Статистика'


# ========== ПОДСИСТЕМА GENERATION ==========

@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    """
    Административный интерфейс для управления действиями генерации контента.
    
    Запрещает создание новых действий и изменение поля name.
    Действия создаются автоматически при миграции из settings.py.
    """
    list_display = (
        'name',
        'label',
        'icon',
        'get_prompts_display',
    )
    list_filter = (
        'name',
    )
    search_fields = (
        'name',
        'label',
    )
    readonly_fields = (
        'name',
    )
    ordering = ('name',)

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'label', 'icon')
        }),
        ('Промпты', {
            'fields': ('system_prompt', 'prompt'),
            'description': 'Настройте промпты для данного действия'
        }),
    )

    def get_prompts_display(self, obj):
        """
        Отображает информацию о промптах в списке объектов.
        """
        prompts = []
        if obj.system_prompt:
            prompts.append(f'Системный: {obj.system_prompt.name}')
        if obj.prompt:
            prompts.append(f'Основной: {obj.prompt.name}')
        
        if prompts:
            return format_html(
                '<div style="font-size: 11px; color: #666;">{}</div>',
                ' | '.join(prompts)
            )
        return '-'
    get_prompts_display.short_description = 'Промпты'

    def has_add_permission(self, request):
        """
        Запрещает создание новых действий.
        Действия создаются автоматически при миграции из settings.py.
        """
        return False

    def has_delete_permission(self, request, obj=None):
        """
        Запрещает удаление действий.
        """
        return False


@admin.register(ContentGenerator)
class ContentGeneratorAdmin(admin.ModelAdmin):
    """
    Административный интерфейс для управления генераторами контента.
    Включает валидацию уникальности content_type на уровне формы.
    """
    form = ContentGeneratorForm
    list_display = (
        'content_type',
        'agent',
        'get_actions_display',
        'get_prompts_display',
    )
    list_filter = (
        'content_type',
        'agent',
    )
    search_fields = (
        'content_type__model',
        'content_type__app_label',
    )
    filter_horizontal = (
        'actions',
    )
    ordering = ('content_type',)

    fieldsets = (
        ('Основная информация', {
            'fields': ('content_type', 'agent')
        }),
        ('Действия', {
            'fields': ('actions',),
            'description': 'Выберите доступные действия для генерации контента в данной модели. Промпты настраиваются для каждого действия отдельно.'
        }),
    )

    def get_actions_display(self, obj):
        """
        Отображает список действий в списке объектов.
        """
        if obj.actions.exists():
            actions_list = [f"{action.icon} {action.label}" for action in obj.actions.all()]
            return format_html(
                '<div style="font-size: 11px;">{}</div>',
                ' | '.join(actions_list)
            )
        return '-'
    get_actions_display.short_description = 'Действия'

    def get_prompts_display(self, obj):
        """
        Отображает информацию о промптах из связанных действий.
        """
        prompts_info = []
        for action in obj.actions.all():
            action_prompts = []
            if action.system_prompt:
                action_prompts.append(f'С: {action.system_prompt.name}')
            if action.prompt:
                action_prompts.append(f'О: {action.prompt.name}')
            if action_prompts:
                prompts_info.append(f'{action.label} ({", ".join(action_prompts)})')
        
        if prompts_info:
            return format_html(
                '<div style="font-size: 11px; color: #666;">{}</div>',
                ' | '.join(prompts_info)
            )
        return '-'
    get_prompts_display.short_description = 'Промпты (из действий)'

