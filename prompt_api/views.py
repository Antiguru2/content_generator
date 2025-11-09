"""
API ViewSets для подсистемы Prompts.
Предоставляет REST API для управления версиями промптов.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from content_generator.models import PromptVersion
from content_generator.serializers import (
    PromptVersionSerializer,
    PromptVersionDetailSerializer,
    PromptVersionCreateSerializer,
    PromptVersionUpdateSerializer,
)
from content_generator.utils import compare_prompt_versions
from content_generator.prompt_api.permissions import AdminOrEngineerPermission, AdminPermission


# ========== ПОДСИСТЕМА PROMPTS ==========

class PromptVersionViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления версиями промптов.
    
    Предоставляет следующие операции:
    - list: список всех версий промптов
    - retrieve: детальный просмотр версии с статистикой
    - create: создание новой версии
    - update: обновление версии (с умным версионированием)
    - partial_update: частичное обновление версии
    - destroy: удаление версии (только для admin)
    - clone: клонирование версии
    - compare: сравнение двух версий
    """
    queryset = PromptVersion.objects.all().order_by('-version_number')
    permission_classes = [IsAuthenticated, AdminOrEngineerPermission]
    
    def get_serializer_class(self):
        """
        Возвращает соответствующий сериализатор в зависимости от действия.
        """
        if self.action == 'retrieve':
            return PromptVersionDetailSerializer
        elif self.action == 'create':
            return PromptVersionCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return PromptVersionUpdateSerializer
        return PromptVersionSerializer
    
    def get_permissions(self):
        """
        Настраивает права доступа в зависимости от действия.
        """
        if self.action == 'destroy':
            # Удаление доступно только администраторам
            return [IsAuthenticated(), AdminPermission()]
        # Остальные действия доступны admin или engineer
        return [IsAuthenticated(), AdminOrEngineerPermission()]
    
    def perform_create(self, serializer):
        """
        Создает новую версию промпта.
        Автоматически заполняет engineer_name из текущего пользователя, если не указан.
        """
        # Если engineer_name не указан, используем имя текущего пользователя
        if not serializer.validated_data.get('engineer_name'):
            user = self.request.user
            engineer_name = user.get_full_name() or user.username
            serializer.save(engineer_name=engineer_name)
        else:
            serializer.save()
    
    def destroy(self, request, *args, **kwargs):
        """
        Удаляет версию промпта.
        Проверяет использование версии и запрещает удаление используемых версий.
        """
        instance = self.get_object()
        
        # Проверяем использование версии
        generated_count = instance.get_generated_content_count()
        if generated_count > 0:
            return Response(
                {
                    'error': 'Нельзя удалить версию промпта, которая используется в сгенерированном контенте.',
                    'generated_content_count': generated_count,
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'], url_path='clone')
    def clone(self, request, pk=None):
        """
        Клонирует версию промпта.
        Создает новую версию с копией содержимого и автоматически генерирует описание.
        
        POST /api/prompt-versions/<id>/clone/
        """
        original_version = self.get_object()
        
        # Генерируем номер новой версии
        new_version_number = PromptVersion.get_next_version_number()
        
        # Создаем описание для клона
        clone_description = f'Клон версии {original_version.version_number}: {original_version.description}'
        
        # Получаем имя инженера из текущего пользователя
        user = request.user
        engineer_name = user.get_full_name() or user.username
        
        # Создаем новую версию с копией содержимого
        cloned_version = PromptVersion.objects.create(
            version_number=new_version_number,
            description=clone_description,
            prompt_content=original_version.prompt_content,
            engineer_name=engineer_name,
        )
        
        # Используем детальный сериализатор для ответа
        serializer = PromptVersionDetailSerializer(cloned_version)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'], url_path='compare/(?P<id1>[^/.]+)/(?P<id2>[^/.]+)')
    def compare(self, request, id1=None, id2=None):
        """
        Сравнивает две версии промптов.
        
        GET /api/prompt-versions/compare/<id1>/<id2>/
        
        Параметры:
        - mode (optional): режим отображения ('side-by-side' или 'unified-diff', по умолчанию 'side-by-side')
        
        Возвращает:
        - Информацию о двух версиях
        - Результаты сравнения (side_by_side, unified_diff)
        - Статистику изменений (added, removed, changed, similarity)
        """
        # Получаем объекты версий
        version1 = get_object_or_404(PromptVersion, pk=id1)
        version2 = get_object_or_404(PromptVersion, pk=id2)
        
        # Выполняем сравнение
        comparison_result = compare_prompt_versions(
            version1.prompt_content,
            version2.prompt_content
        )
        
        # Получаем режим отображения из GET параметров
        display_mode = request.GET.get('mode', 'side-by-side')
        
        # Сериализуем версии
        version1_serializer = PromptVersionSerializer(version1)
        version2_serializer = PromptVersionSerializer(version2)
        
        return Response({
            'version1': version1_serializer.data,
            'version2': version2_serializer.data,
            'comparison': {
                'side_by_side': comparison_result['side_by_side'],
                'unified_diff': comparison_result['unified_diff'],
                'stats': comparison_result['stats'],
                'truncated': comparison_result['truncated'],
            },
            'display_mode': display_mode,
        })

