from django.views.generic import TemplateView, ListView
from django.utils.decorators import method_decorator
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect
from django.urls import reverse

from .models import PromptVersion


# ========== ПОДСИСТЕМА PROMPTS ==========

@method_decorator(staff_member_required, name='dispatch')
class PromptVersionListView(ListView):
    """
    Представление для отображения списка версий промптов.
    Включает пагинацию, сортировку и подсчет статистики для каждой версии.
    """
    model = PromptVersion
    template_name = 'content_generator/prompt_versions/list.html'
    context_object_name = 'prompt_versions'
    paginate_by = 10
    ordering = ['-version_number']  # Сортировка по version_number (убывание)

    def get_queryset(self):
        """
        Возвращает queryset с дополнительной аннотацией статистики.
        """
        queryset = super().get_queryset()
        # Сортировка уже настроена в Meta модели и через ordering
        return queryset

    def get_context_data(self, **kwargs):
        """
        Добавляет в контекст статистику для каждой версии и выбранные версии для сравнения.
        """
        context = super().get_context_data(**kwargs)
        
        # Получаем выбранные версии для сравнения из GET параметров
        selected_versions = self.request.GET.getlist('compare')
        # Ограничиваем максимум 2 версии и фильтруем только валидные ID
        selected_versions = []
        for v in self.request.GET.getlist('compare')[:2]:
            try:
                if v.isdigit():
                    selected_versions.append(int(v))
            except (ValueError, TypeError):
                continue
        
        # Добавляем статистику для каждой версии в списке
        versions_with_stats = []
        for version in context['prompt_versions']:
            stats = {
                'generated_count': version.get_generated_content_count(),
                'reviewed_count': version.get_reviewed_content_count(),
                'review_percentage': version.get_review_percentage(),
                'average_rating': version.get_average_rating(),
            }
            versions_with_stats.append({
                'version': version,
                'stats': stats,
                'is_selected': version.id in selected_versions,
            })
        
        context['versions_with_stats'] = versions_with_stats
        context['selected_versions'] = selected_versions
        context['can_compare'] = len(selected_versions) == 2
        
        # URL для сравнения, если выбрано 2 версии
        # TODO: Будет реализовано в следующем этапе (PromptVersionCompareView)
        if len(selected_versions) == 2:
            context['compare_url'] = '#'  # Временно, до реализации сравнения
        
        return context

    def post(self, request, *args, **kwargs):
        """
        Обрабатывает POST запрос для выбора версий для сравнения.
        Перенаправляет на GET с параметрами compare.
        """
        selected_versions = request.POST.getlist('compare')
        # Ограничиваем максимум 2 версии и фильтруем только валидные ID
        valid_versions = []
        for v in selected_versions[:2]:
            try:
                if v.isdigit():
                    valid_versions.append(v)
            except (ValueError, TypeError):
                continue
        selected_versions = valid_versions
        
        # Формируем URL с параметрами compare
        url = reverse('prompt_version_list')
        if selected_versions:
            params = '&'.join([f'compare={v}' for v in selected_versions])
            url = f'{url}?{params}'
        
        return redirect(url)


# ========== ПОДСИСТЕМА GENERATION ==========

@method_decorator(staff_member_required, name='dispatch')
class ContentGeneratorWidgetView(TemplateView):
    """Отображает виджет генерации контента в айфрейме без передачи GET-параметров в контекст."""
    template_name = 'custom_admin/content_generator_widget.html'
