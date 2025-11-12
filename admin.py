from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.contrib import messages

from .models import Prompt, PromptVersion
from .forms import PromptVersionForm


# ========== ПОДСИСТЕМА PROMPTS ==========

@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    """
    Административный интерфейс для управления типами промптов.
    """
    list_display = (
        'prompt_type',
        'name',
        'is_active',
        'get_versions_count',
        'created_at',
    )
    list_filter = (
        'is_active',
        'prompt_type',
        'created_at',
    )
    search_fields = (
        'name',
        'description',
        'prompt_type',
    )
    readonly_fields = (
        'created_at',
        'updated_at',
    )
    ordering = ('prompt_type',)

    fieldsets = (
        ('Основная информация', {
            'fields': ('prompt_type', 'name', 'description', 'is_active')
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
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
        'prompt__prompt_type',
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
            prompt_name = obj.prompt.get_prompt_type_display() if obj.prompt else 'Unknown'
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

