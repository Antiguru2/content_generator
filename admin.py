from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import PromptVersion


# ========== ПОДСИСТЕМА PROMPTS ==========

@admin.register(PromptVersion)
class PromptVersionAdmin(admin.ModelAdmin):
    """
    Административный интерфейс для управления версиями промптов.
    """
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
            'fields': ('prompt_content',)
        }),
    )

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

