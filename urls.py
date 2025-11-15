from django.urls import path, include
from . import api
from . import views

urlpatterns = [
    # Новый унифицированный endpoint
    path('generate/', api.generate, name='generate'),
    # API endpoint для получения actions по generator_id
    path('get_actions/', api.get_actions, name='get_actions'),
    # Виджет для айфрейма
    path('content_generator_widget/', views.ContentGeneratorWidgetView.as_view(), name='content_generator_widget'),
    
    # ========== ПОДСИСТЕМА PROMPTS ==========
    # Список версий промптов
    path('admin/prompt-versions/', views.PromptVersionListView.as_view(), name='prompt_version_list'),
    # Создание новой версии промпта
    path('admin/prompt-versions/add/', views.PromptVersionCreateView.as_view(), name='prompt_version_create'),
    # Редактирование версии промпта
    path('admin/prompt-versions/<int:id>/edit/', views.PromptVersionUpdateView.as_view(), name='prompt_version_update'),
    # Клонирование версии промпта
    path('admin/prompt-versions/<int:id>/clone/', views.PromptVersionCloneView.as_view(), name='prompt_version_clone'),
    # Удаление версии промпта
    path('admin/prompt-versions/<int:id>/delete/', views.PromptVersionDeleteView.as_view(), name='prompt_version_delete'),
    # Детальный просмотр версии промпта
    path('admin/prompt-versions/<int:id>/', views.PromptVersionDetailView.as_view(), name='prompt_version_detail'),
    # Сравнение версий промптов
    path('admin/prompt-versions/compare/<int:id1>/<int:id2>/', views.PromptVersionCompareView.as_view(), name='prompt_version_compare'),
    
    # ========== API ПОДСИСТЕМА PROMPTS ==========
    # REST API для версий промптов
    path('api/', include('content_generator.prompt_api.urls')),
    
    # Старые endpoints для обратной совместимости
    path('set_seo_params/', api.set_seo_params, name='set_seo_params'),
    path('set_description/', api.set_description, name='set_description'),
    path('upgrade_name/', api.upgrade_name, name='upgrade_name'),
    path('set_some_params/', api.set_some_params, name='set_some_params'),
    path('change_img/', api.change_img, name='change_img'),
]