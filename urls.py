from django.urls import path
from content_generator import api
from content_generator import views

urlpatterns = [
    # Новый унифицированный endpoint
    path('generate/', api.generate, name='generate'),
    # Виджет для айфрейма
    path('content_generator_widget/', views.ContentGeneratorWidgetView.as_view(), name='content_generator_widget'),
    
    # ========== ПОДСИСТЕМА PROMPTS ==========
    # Список версий промптов
    path('admin/prompt-versions/', views.PromptVersionListView.as_view(), name='prompt_version_list'),
    # Детальный просмотр версии промпта
    path('admin/prompt-versions/<int:id>/', views.PromptVersionDetailView.as_view(), name='prompt_version_detail'),
    
    # Старые endpoints для обратной совместимости
    path('set_seo_params/', api.set_seo_params, name='set_seo_params'),
    path('set_description/', api.set_description, name='set_description'),
    path('upgrade_name/', api.upgrade_name, name='upgrade_name'),
    path('set_some_params/', api.set_some_params, name='set_some_params'),
    path('change_img/', api.change_img, name='change_img'),
]