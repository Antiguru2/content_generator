import traceback
import threading

from django.apps import apps
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, HttpResponse
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.shortcuts import get_current_site

from content_generator.models import PromptVersion, Prompt
from content_generator.ai_interface_adapter import create_generation_task
from content_generator.utils import get_prompt_for_action, ACTION_TO_PROMPT_TYPE


# Словарь для маппинга действий на методы
ACTION_METHODS = {
    'set_seo_params': 'set_seo_params',
    'set_description': 'set_description', 
    'upgrade_name': 'upgrade_name',
    'set_some_params': 'set_some_params',
    'update_html_constructor': 'update_html_constructor',
    # 'change_img': 'get_images_by_text',  # TODO: реализовать
}


@login_required()
def generate(request):
    """
    Унифицированный API endpoint для генерации контента.
    
    Параметры:
        - class_name (str): Имя класса модели (например, 'product', 'category')
        - model_id (int): ID объекта модели
        - action (str): Действие для выполнения (set_seo_params, set_description, etc.)
        - prompt_version_id (int, optional): ID версии промпта (если не указан, используется последняя)
        - additional_prompt (str, optional): Дополнительный промпт от пользователя
        - async_mode (bool, optional): Выполнять асинхронно (по умолчанию False)
    
    Возвращает:
        JSON: { "status": "ok", "task_id": <id> } или { "status": "error", "message": <error> }
    """
    print('generate')
    try:
        # Получаем параметры
        natural_key = request.GET.get('natural_key')
        model_id = request.GET.get('model_id')
        action = request.GET.get('action')
        prompt_version_id = request.GET.get('prompt_version_id')
        additional_prompt = request.GET.get('additional_prompt', '')
        async_mode = request.GET.get('async_mode', 'false').lower() == 'true'
        
        # Валидация
        if not natural_key or not model_id or not action:
            return JsonResponse({
                'status': 'error',
                'message': 'Отсутствуют обязательные параметры: class_name, model_id, action'
            }, status=400)
        
        if action not in ACTION_METHODS:
            return JsonResponse({
                'status': 'error',
                'message': f'Неизвестное действие: {action}'
            }, status=400)
        
        # Получаем модель и объект
        try:
            Model = apps.get_model(natural_key)
            model_instance = get_object_or_404(Model, id=model_id)
        except LookupError:
            return JsonResponse({
                'status': 'error',
                'message': f'Модель {natural_key} не найдена'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Объект не найден: {str(e)}'
            }, status=404)
        
        # Проверяем наличие метода у модели
        method_name = ACTION_METHODS[action]
        if not hasattr(model_instance, method_name):
            return JsonResponse({
                'status': 'error',
                'message': f'Модель {natural_key} не поддерживает действие {action}'
            }, status=400)
        
        # Получаем версию промпта
        prompt_version = None
        if prompt_version_id:
            try:
                prompt_version = PromptVersion.objects.get(id=prompt_version_id)
            except PromptVersion.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Версия промпта с ID {prompt_version_id} не найдена'
                }, status=404)
        else:
            # Используем промпт для конкретного действия
            prompt_version = get_prompt_for_action(action)
            if not prompt_version:
                prompt_type = ACTION_TO_PROMPT_TYPE.get(action, 'unknown')
                return JsonResponse({
                    'status': 'error',
                    'message': f'Не найден активный промпт для действия "{action}" (тип: {prompt_type}). Создайте промпт и его версию перед генерацией.'
                }, status=404)
        
        # Если асинхронный режим - создаем задачу через ai_interface
        if async_mode:
            try:
                from ai_interface.models import AIProvider
                
                # Получаем ContentType для модели
                content_type = ContentType.objects.get_for_model(model_instance)
                
                # Получаем домен
                site = get_current_site(request)
                domain = site.domain if site else None
                
                # Формируем дополнительные данные
                additional_data = {}
                if additional_prompt:
                    additional_data['additional_prompt'] = additional_prompt
                
                # Создаем задачу через адаптер
                task = create_generation_task(
                    prompt_version=prompt_version,
                    content_type=content_type,
                    object_id=int(model_id),
                    action=action,
                    additional_data=additional_data if additional_data else None,
                    provider=None,  # Используем AILENGO из настроек
                    domain=domain
                )
                
                return JsonResponse({
                    'status': 'ok',
                    'task_id': task.id,
                    'prompt_version_id': prompt_version.id,
                    'message': 'Задача создана и отправлена в AI-провайдер'
                })
                
            except ImportError:
                # Если ai_interface недоступен, выполняем синхронно
                pass
            except Exception as e:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Ошибка при создании задачи: {str(e)}',
                    'traceback': traceback.format_exc()
                }, status=500)
        
        # Синхронное выполнение
        execute_generation_action(model_instance, action, additional_prompt)
        
        return JsonResponse({
            'status': 'ok',
            'success': True,
            'message': f'Действие {action} выполнено успешно'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        }, status=500)


def execute_generation_action(model_instance, action, additional_prompt=''):
    """
    Выполняет действие генерации для модели.
    
    Вызывает соответствующий метод модели на основе действия.
    Некоторые действия (например, set_some_params) поддерживают дополнительный промпт.
    
    Args:
        model_instance: Экземпляр модели (Product, Category и т.д.)
        action: Название действия (set_seo_params, set_description, upgrade_name, set_some_params)
        additional_prompt: Дополнительный промпт от пользователя (используется для set_some_params)
    """
    # Получаем имя метода из словаря маппинга действий
    method_name = ACTION_METHODS[action]
    # Получаем метод модели через рефлексию
    method = getattr(model_instance, method_name)
    
    # Для действий, поддерживающих дополнительный промпт (например, set_some_params)
    # передаем additional_prompt как аргумент
    if action in ['set_some_params'] and additional_prompt:
        method(additional_prompt)
    else:
        # Для остальных действий вызываем метод без аргументов
        method()


# ============================================================================
# Старые endpoints для обратной совместимости
# ============================================================================

@login_required()
def set_seo_params(request):
    """API endpoint для генерации SEO параметров"""
    context = {}
    class_name = request.GET.get('class_name')
    model_id = request.GET.get('model_id')

    Model = apps.get_model('store', class_name)
    model = get_object_or_404(Model, id=model_id)
    model.set_seo_params()
     
    return redirect(model.get_admin_url() + '#set_seo_params_button')


@login_required()
def set_description(request):
    """API endpoint для генерации описания"""
    context = {}
    class_name = request.GET.get('class_name')
    model_id = request.GET.get('model_id')

    Model = apps.get_model('store', class_name)
    model = get_object_or_404(Model, id=model_id)
    model.set_description()
     
    return redirect(model.get_admin_url())


@login_required()
def upgrade_name(request):
    """API endpoint для улучшения названия"""
    context = {}
    class_name = request.GET.get('class_name')
    model_id = request.GET.get('model_id')

    Model = apps.get_model('store', class_name)
    model = get_object_or_404(Model, id=model_id)
    model.upgrade_name()
     
    return redirect(model.get_admin_url())


@login_required()
def set_some_params(request):
    """API endpoint для комплексного улучшения параметров"""
    class_name = request.GET.get('class_name')
    model_id = request.GET.get('model_id')
    additional_prompt = request.GET.get('additional_prompt')
    redirect_url = request.GET.get('redirect_url')

    print('class_name', class_name)
    Model = apps.get_model('store', class_name)
    model = get_object_or_404(Model, id=model_id)
    model.set_some_params(additional_prompt)
     
    if redirect_url:
        return redirect(redirect_url)

    return redirect(model.get_admin_url())


@login_required()
def change_img(request):
    """API endpoint для выбора изображения из Яндекс.Картинок"""
    # TODO: Реализовать функциональность выбора изображения
    # Пока что возвращаем заглушку
    return HttpResponse("Функция выбора изображения будет реализована позже")
