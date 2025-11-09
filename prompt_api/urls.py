"""
URL маршруты для API подсистемы Prompts.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from content_generator.prompt_api.views import PromptVersionViewSet

# Создаем роутер для автоматической генерации маршрутов
router = DefaultRouter()
router.register(r'prompt-versions', PromptVersionViewSet, basename='prompt-version')

urlpatterns = [
    path('', include(router.urls)),
]

