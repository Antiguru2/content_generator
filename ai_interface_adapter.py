"""
Адаптер для интеграции с ai_interface.

Предоставляет функции для создания задач генерации контента через ai_interface
и обработки результатов генерации.
"""

from typing import Optional, Dict, Any
from django.apps import apps
from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType

from ai_interface.models import AITask, AIAgent
from content_generator.models import PromptVersion, GeneratedContent


def create_generation_task(
    prompt_version: PromptVersion,
    content_type: ContentType,
    object_id: int,
    action: str,
    additional_data: Optional[Dict[str, Any]] = None,
    agent: Optional[AIAgent] = None,
    domain: Optional[str] = None
) -> AITask:
    """
    Создает задачу генерации контента через ai_interface с использованием PromptVersion.
    
    Args:
        prompt_version: Версия промпта для использования в генерации
        content_type: Тип контента (ContentType для связанного объекта)
        object_id: ID связанного объекта
        action: Действие для выполнения (set_seo_params, set_description, etc.)
        additional_data: Дополнительные данные для генерации (например, additional_prompt)
        agent: AI-агент (обязателен)
        domain: Домен для построения webhook URL (если None, берется из Site)
    
    Returns:
        AITask: Созданная задача
    
    Raises:
        Exception: При ошибках создания задачи или вызова агента
    """
    # Получаем домен, если не указан
    if domain is None:
        try:
            site = Site.objects.get_current()
            domain = site.domain
        except Exception:
            # Fallback на настройки, если Site не настроен
            from django.conf import settings
            domain = getattr(settings, 'SITE_DOMAIN', 'localhost')
    
    # Формируем данные для задачи
    # context_data - данные для обработки в процессорах
    context_data = {
        'prompt_version_id': prompt_version.id,
        'class_name': content_type.model,
        'model_id': object_id,
        'action': action,
        'prompt_content': prompt_version.prompt_content,
    }
    
    # Добавляем дополнительные данные, если есть
    if additional_data:
        context_data.update(additional_data)
    
    # payload - данные для отправки AI-агенту
    payload = {
        'prompt': prompt_version.prompt_content,
    }
    
    # Если есть additional_prompt, добавляем его в payload
    if additional_data and 'additional_prompt' in additional_data:
        payload['additional_prompt'] = additional_data['additional_prompt']
    
    # Определяем эндпоинт на основе действия
    endpoint = f'content_generator_{action}'
    
    # Создаем и отправляем задачу
    task = AITask.create_and_dispatch(
        endpoint=endpoint,
        payload=payload,
        context_data=context_data,
        agent=agent
    )
    
    return task


def process_generation_result(ai_task: AITask) -> Optional[GeneratedContent]:
    """
    Обрабатывает результат генерации от ai_interface и создает/обновляет GeneratedContent.
    
    Извлекает prompt_version_id из данных задачи, создает GeneratedContent
    и связывает его с PromptVersion.
    
    Args:
        ai_task: Задача из ai_interface с результатом генерации
    
    Returns:
        GeneratedContent: Созданный или обновленный объект GeneratedContent, или None при ошибке
    """
    try:
        # Извлекаем данные из задачи
        task_data = ai_task.context_data or {}
        result_data = ai_task.result or {}
        
        # Получаем prompt_version_id из данных задачи
        prompt_version_id = task_data.get('prompt_version_id')
        if not prompt_version_id:
            print(f'Warning: prompt_version_id not found in task data for AITask #{ai_task.id}')
            return None
        
        # Получаем PromptVersion
        try:
            prompt_version = PromptVersion.objects.get(id=prompt_version_id)
        except PromptVersion.DoesNotExist:
            print(f'Error: PromptVersion with id {prompt_version_id} not found')
            return None
        
        # Извлекаем данные для создания GeneratedContent
        class_name = task_data.get('class_name')
        model_id = task_data.get('model_id')
        
        if not class_name or not model_id:
            print(f'Error: class_name or model_id not found in task data for AITask #{ai_task.id}')
            return None
        
        # Получаем ContentType
        try:
            content_type = ContentType.objects.get(app_label='store', model=class_name.lower())
        except ContentType.DoesNotExist:
            print(f'Error: ContentType for {class_name} not found')
            return None
        
        # Определяем статус на основе статуса задачи
        if ai_task.status == 'SUCCESS':
            status = 'SUCCESS'
        elif ai_task.status == 'FAILURE':
            status = 'FAILURE'
        elif ai_task.status in ['PREPROCESSING', 'POSTPROCESSING', 'PENDING']:
            status = 'PROCESSING'
        else:
            status = 'PENDING'
        
        # Ищем существующий GeneratedContent или создаем новый
        generated_content, created = GeneratedContent.objects.get_or_create(
            ai_task=ai_task,
            defaults={
                'prompt_version': prompt_version,
                'content_type': content_type,
                'object_id': model_id,
                'generated_data': result_data,
                'status': status,
            }
        )
        
        # Если объект уже существовал, обновляем его
        if not created:
            generated_content.prompt_version = prompt_version
            generated_content.generated_data = result_data
            generated_content.status = status
            generated_content.save()
        
        return generated_content
        
    except Exception as e:
        print(f'Error processing generation result for AITask #{ai_task.id}: {str(e)}')
        import traceback
        traceback.print_exc()
        return None


def link_content_with_prompt(generated_content: GeneratedContent, prompt_version: PromptVersion) -> None:
    """
    Связывает GeneratedContent с PromptVersion.
    
    Args:
        generated_content: Объект GeneratedContent
        prompt_version: Версия промпта для связывания
    """
    generated_content.prompt_version = prompt_version
    generated_content.save()

