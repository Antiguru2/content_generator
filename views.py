from django.views.generic import TemplateView, ListView, DetailView
from django.utils.decorators import method_decorator
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.db.models import Count

from .models import PromptVersion, GeneratedContent


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


@method_decorator(staff_member_required, name='dispatch')
class PromptVersionDetailView(DetailView):
    """
    Представление для детального просмотра версии промпта.
    Отображает полную информацию о версии, статистику использования,
    распределение оценок и список связанного сгенерированного контента.
    """
    model = PromptVersion
    template_name = 'content_generator/prompt_versions/detail.html'
    context_object_name = 'version'
    pk_url_kwarg = 'id'

    def get_object(self, queryset=None):
        """
        Возвращает объект версии промпта по ID из URL.
        """
        if queryset is None:
            queryset = self.get_queryset()
        pk = self.kwargs.get(self.pk_url_kwarg)
        return get_object_or_404(queryset, pk=pk)

    def get_context_data(self, **kwargs):
        """
        Добавляет в контекст статистику использования, распределение оценок
        и список связанного сгенерированного контента.
        """
        context = super().get_context_data(**kwargs)
        version = context['version']

        # Статистика использования (4 метрики)
        stats = {
            'generated_count': version.get_generated_content_count(),
            'reviewed_count': version.get_reviewed_content_count(),
            'review_percentage': version.get_review_percentage(),
            'average_rating': version.get_average_rating(),
        }
        context['stats'] = stats

        # Распределение оценок (если есть система оценок)
        rating_distribution = {}
        try:
            # Получаем распределение оценок для данной версии
            rating_data = GeneratedContent.objects.filter(
                prompt_version=version,
                rating__isnull=False
            ).values('rating').annotate(count=Count('rating')).order_by('rating')
            
            # Инициализируем все возможные оценки (1-5) нулями
            for rating_value in range(1, 6):
                rating_distribution[rating_value] = 0
            
            # Заполняем реальными данными
            for item in rating_data:
                rating_distribution[item['rating']] = item['count']
        except Exception:
            # Если возникла ошибка, просто оставляем все нули
            for rating_value in range(1, 6):
                rating_distribution[rating_value] = 0
        
        context['rating_distribution'] = rating_distribution
        context['has_ratings'] = any(count > 0 for count in rating_distribution.values())

        # Список связанного сгенерированного контента (первые 20)
        try:
            generated_content = GeneratedContent.objects.filter(
                prompt_version=version
            ).select_related('content_type', 'ai_task')[:20]
            context['generated_content'] = generated_content
            context['generated_content_count'] = version.get_generated_content_count()
            context['has_more_content'] = version.get_generated_content_count() > 20
        except Exception:
            context['generated_content'] = []
            context['generated_content_count'] = 0
            context['has_more_content'] = False

        return context


# ========== ПОДСИСТЕМА GENERATION ==========

@method_decorator(staff_member_required, name='dispatch')
class ContentGeneratorWidgetView(TemplateView):
    """Отображает виджет генерации контента в айфрейме без передачи GET-параметров в контекст."""
    template_name = 'custom_admin/content_generator_widget.html'
