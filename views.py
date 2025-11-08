from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.utils.decorators import method_decorator
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.db.models import Count

from .models import PromptVersion, GeneratedContent
from .forms import PromptVersionForm


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


@method_decorator(staff_member_required, name='dispatch')
class PromptVersionCreateView(CreateView):
    """
    Представление для создания новой версии промпта.
    Автоматически генерирует номер версии и заполняет engineer_name из текущего пользователя.
    """
    model = PromptVersion
    form_class = PromptVersionForm
    template_name = 'content_generator/prompt_versions/form.html'
    
    def get_form_kwargs(self):
        """
        Передает текущего пользователя в форму для автоматического заполнения engineer_name.
        """
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        """
        Обрабатывает валидную форму:
        - Автоматически генерирует номер версии
        - Сохраняет объект
        - Перенаправляет на страницу детального просмотра созданной версии.
        """
        # Автоматическая генерация номера версии
        form.instance.version_number = PromptVersion.get_next_version_number()
        
        # Сохраняем объект
        self.object = form.save()
        
        # Редирект на страницу детального просмотра созданной версии
        return redirect('prompt_version_detail', id=self.object.id)
    
    def get_context_data(self, **kwargs):
        """
        Добавляет в контекст заголовок страницы.
        """
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Создание новой версии промпта'
        context['is_create'] = True
        return context


@method_decorator(staff_member_required, name='dispatch')
class PromptVersionUpdateView(UpdateView):
    """
    Представление для редактирования версии промпта.
    Реализует логику "умного версионирования":
    - При изменении prompt_content → создание новой версии
    - При изменении только description → обновление текущей версии
    """
    model = PromptVersion
    form_class = PromptVersionForm
    template_name = 'content_generator/prompt_versions/form.html'
    pk_url_kwarg = 'id'
    context_object_name = 'version'
    
    def get_object(self, queryset=None):
        """
        Возвращает объект версии промпта по ID из URL.
        """
        if queryset is None:
            queryset = self.get_queryset()
        pk = self.kwargs.get(self.pk_url_kwarg)
        return get_object_or_404(queryset, pk=pk)
    
    def get_form_kwargs(self):
        """
        Передает текущего пользователя в форму для автоматического заполнения engineer_name.
        """
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        """
        Обрабатывает валидную форму с реализацией "умного версионирования":
        - Проверяет изменения в prompt_content
        - Создает новую версию при изменении содержимого
        - Обновляет текущую версию при изменении только описания
        - Показывает уведомления пользователю о действиях
        """
        # Получаем оригинальный объект из базы данных до изменений
        original_obj = PromptVersion.objects.get(pk=self.object.pk)
        original_prompt_content = original_obj.prompt_content
        new_prompt_content = form.cleaned_data.get('prompt_content', '')
        new_description = form.cleaned_data.get('description', '')
        new_engineer_name = form.cleaned_data.get('engineer_name', '')
        
        # Проверяем, изменилось ли содержимое промпта
        if original_prompt_content != new_prompt_content:
            # Создаем новую версию при изменении содержимого
            new_version_number = PromptVersion.get_next_version_number()
            new_version = PromptVersion(
                version_number=new_version_number,
                description=new_description,
                prompt_content=new_prompt_content,
                engineer_name=new_engineer_name,
            )
            new_version.save()
            
            # Уведомление о создании новой версии
            messages.success(
                self.request,
                f'Создана новая версия промпта #{new_version_number}: "{new_description[:50]}". '
                f'Старая версия #{original_obj.version_number} сохранена без изменений.'
            )
            
            # Редирект на страницу детального просмотра новой версии
            return redirect('prompt_version_detail', id=new_version.id)
        else:
            # Обновляем только описание текущей версии
            original_obj.description = new_description
            original_obj.engineer_name = new_engineer_name
            original_obj.save()
            
            # Уведомление об обновлении текущей версии
            messages.info(
                self.request,
                f'Версия промпта #{original_obj.version_number} обновлена (изменено только описание).'
            )
            
            # Редирект на страницу детального просмотра обновленной версии
            return redirect('prompt_version_detail', id=original_obj.id)
    
    def get_context_data(self, **kwargs):
        """
        Добавляет в контекст заголовок страницы, информацию о версии и статистику.
        """
        context = super().get_context_data(**kwargs)
        version = context['version']
        
        context['page_title'] = f'Редактирование версии промпта #{version.version_number}'
        context['is_create'] = False
        
        # Статистика использования (для отображения в форме)
        stats = {
            'generated_count': version.get_generated_content_count(),
            'reviewed_count': version.get_reviewed_content_count(),
            'review_percentage': version.get_review_percentage(),
            'average_rating': version.get_average_rating(),
        }
        context['stats'] = stats
        
        return context


@method_decorator(staff_member_required, name='dispatch')
class PromptVersionCloneView(View):
    """
    Представление для клонирования версии промпта.
    Создает новую версию с копией содержимого и автоматически генерирует описание.
    """
    
    def get(self, request, *args, **kwargs):
        """
        Обрабатывает GET запрос для клонирования версии:
        - Получает оригинальную версию по ID
        - Создает новую версию с копией содержимого
        - Автоматически генерирует описание "Клон версии {номер}: {описание}"
        - Редиректит на страницу редактирования новой версии
        """
        # Получаем оригинальную версию
        original_version = get_object_or_404(PromptVersion, pk=kwargs.get('id'))
        
        # Генерируем номер новой версии
        new_version_number = PromptVersion.get_next_version_number()
        
        # Создаем описание для клона
        clone_description = f'Клон версии {original_version.version_number}: {original_version.description}'
        
        # Создаем новую версию с копией содержимого
        cloned_version = PromptVersion(
            version_number=new_version_number,
            description=clone_description,
            prompt_content=original_version.prompt_content,
            engineer_name=request.user.get_full_name() or request.user.username,
        )
        cloned_version.save()
        
        # Уведомление о создании клона
        messages.success(
            request,
            f'Создана копия версии промпта #{original_version.version_number} как версия #{new_version_number}.'
        )
        
        # Редирект на страницу редактирования новой версии
        return redirect('prompt_version_update', id=cloned_version.id)


@method_decorator(staff_member_required, name='dispatch')
class PromptVersionDeleteView(DeleteView):
    """
    Представление для удаления версии промпта.
    Проверяет использование версии (если есть GeneratedContent) и запрещает удаление используемых версий.
    """
    model = PromptVersion
    template_name = 'content_generator/prompt_versions/delete_confirm.html'
    pk_url_kwarg = 'id'
    context_object_name = 'version'
    
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
        Добавляет в контекст информацию об использовании версии и статистику.
        """
        context = super().get_context_data(**kwargs)
        version = context['version']
        
        # Проверка использования версии
        generated_content_count = version.get_generated_content_count()
        context['generated_content_count'] = generated_content_count
        context['is_used'] = generated_content_count > 0
        
        # Если версия используется, получаем примеры использования
        if generated_content_count > 0:
            context['generated_content_examples'] = GeneratedContent.objects.filter(
                prompt_version=version
            )[:5]  # Первые 5 примеров
        
        return context
    
    def get(self, request, *args, **kwargs):
        """
        Обрабатывает GET запрос для отображения страницы подтверждения удаления.
        Проверяет использование версии и запрещает удаление, если версия используется.
        """
        self.object = self.get_object()
        context = self.get_context_data()
        
        # Проверка использования версии
        if context['is_used']:
            messages.error(
                request,
                f'Невозможно удалить версию промпта #{self.object.version_number}, '
                f'так как она используется в {context["generated_content_count"]} '
                f'{"записи" if context["generated_content_count"] == 1 else "записях"} сгенерированного контента.'
            )
            return redirect('prompt_version_detail', id=self.object.id)
        
        return self.render_to_response(context)
    
    def post(self, request, *args, **kwargs):
        """
        Обрабатывает POST запрос для удаления версии.
        Проверяет использование версии перед удалением.
        """
        self.object = self.get_object()
        
        # Повторная проверка использования версии (на случай, если что-то изменилось)
        generated_content_count = self.object.get_generated_content_count()
        if generated_content_count > 0:
            messages.error(
                request,
                f'Невозможно удалить версию промпта #{self.object.version_number}, '
                f'так как она используется в {generated_content_count} '
                f'{"записи" if generated_content_count == 1 else "записях"} сгенерированного контента.'
            )
            return redirect('prompt_version_detail', id=self.object.id)
        
        # Сохраняем информацию о версии для сообщения
        version_number = self.object.version_number
        description = self.object.description
        
        # Удаляем версию
        self.object.delete()
        
        # Уведомление об успешном удалении
        messages.success(
            request,
            f'Версия промпта #{version_number}: "{description[:50]}" успешно удалена.'
        )
        
        # Редирект на список версий
        return redirect('prompt_version_list')
    
    def get_success_url(self):
        """
        Возвращает URL для редиректа после успешного удаления.
        """
        return reverse('prompt_version_list')


# ========== ПОДСИСТЕМА GENERATION ==========

@method_decorator(staff_member_required, name='dispatch')
class ContentGeneratorWidgetView(TemplateView):
    """Отображает виджет генерации контента в айфрейме без передачи GET-параметров в контекст."""
    template_name = 'custom_admin/content_generator_widget.html'
