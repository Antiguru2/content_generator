from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.contrib import messages

from .models import PromptVersion
from .forms import PromptVersionForm


# ========== ПОДСИСТЕМА PROMPTS ==========

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
        'version_number',
        'description',
        'engineer_name',
        'created_at',
        'get_statistics_display',
    )
    list_filter = (
        'created_at',
        'engineer_name',
    )
    search_fields = (
        'description',
        'prompt_content',
        'engineer_name',
    )
    readonly_fields = (
        'version_number',
        'created_at',
    )
    ordering = ('-version_number',)

    fieldsets = (
        ('Основная информация', {
            'fields': ('version_number', 'description', 'engineer_name', 'created_at')
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
        if 'form' not in kwargs:
            kwargs['form'] = PromptVersionForm
        
        # Передаем user в форму через form_kwargs
        if 'form_kwargs' not in kwargs:
            kwargs['form_kwargs'] = {}
        kwargs['form_kwargs']['user'] = request.user
        
        return super().get_form(request, obj, **kwargs)

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
                obj.version_number = PromptVersion.get_next_version_number()
            obj.engineer_name = form.cleaned_data.get('engineer_name', '')
            super().save_model(request, obj, form, change)
            messages.success(
                request,
                f'Создана новая версия промпта #{obj.version_number}: "{obj.description[:50]}"'
            )
        else:
            # Редактирование существующей версии
            original_obj = PromptVersion.objects.get(pk=obj.pk)
            original_prompt_content = original_obj.prompt_content
            new_prompt_content = form.cleaned_data.get('prompt_content', '')
            
            # Проверяем, изменилось ли содержимое промпта
            if original_prompt_content != new_prompt_content:
                # Создаем новую версию
                new_version_number = PromptVersion.get_next_version_number()
                new_version = PromptVersion(
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

