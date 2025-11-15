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


@login_required()
def generate(request):
    """
    Унифицированный API endpoint для генерации контента.
    
    Параметры:
        - generator_id (int): ID генератора контента (обязательный)
        - model_id (int): ID объекта модели (обязательный)
        - action (str): Действие для выполнения (set_seo_params, set_description, etc.)
        - additional_prompt (str, optional): Дополнительный промпт от пользователя
        - async_mode (bool, optional): Выполнять асинхронно (по умолчанию False)
    
    Возвращает:
        JSON: { "status": "ok", "task_id": <id> } или { "status": "error", "message": <error> }
    """
    print('generate')
    try:
        # Получаем параметры
        generator_id = request.GET.get('generator_id')
        model_id = request.GET.get('model_id')
        action = request.GET.get('action')
        additional_prompt = request.GET.get('additional_prompt', '')
        async_mode = request.GET.get('async_mode', 'false').lower() == 'true'
        
        # Валидация
        if not generator_id or not model_id or not action:
            return JsonResponse({
                'status': 'error',
                'message': 'Отсутствуют обязательные параметры: generator_id, model_id, action'
            }, status=400)
        
        # Получаем генератор и извлекаем информацию о модели
        try:
            from content_generator.models import ContentGenerator
            generator = ContentGenerator.objects.get(id=generator_id)
        except ContentGenerator.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'Генератор с ID {generator_id} не найден'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Ошибка при получении генератора: {str(e)}'
            }, status=500)
        
        # Проверяем наличие content_type у генератора
        if not generator.content_type:
            return JsonResponse({
                'status': 'error',
                'message': f'Генератор с ID {generator_id} не имеет настроенного типа контента'
            }, status=400)
        
        # Получаем модель и объект через content_type
        try:
            Model = generator.content_type.model_class()
            if not Model:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Модель для типа контента {generator.content_type} не найдена'
                }, status=404)
            
            model_instance = get_object_or_404(Model, id=model_id)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Объект не найден: {str(e)}'
            }, status=404)
        
        # Проверяем наличие метода у модели
        if not hasattr(model_instance, action):
            natural_key = f"{generator.content_type.app_label}.{generator.content_type.model}"
            return JsonResponse({
                'status': 'error',
                'message': f'Модель {natural_key} не поддерживает действие {action}'
            }, status=400)
        
        # Получаем версию промпта для конкретного действия
        prompt_version = get_prompt_for_action(generator, action)
        if not prompt_version:
            prompt_type = ACTION_TO_PROMPT_TYPE.get(action, 'unknown')
            return JsonResponse({
                'status': 'error',
                'message': f'Не найден активный промпт для действия "{action}" (тип: {prompt_type}). Создайте промпт и его версию перед генерацией.'
            }, status=404)
        
        # Если асинхронный режим - создаем задачу через ai_interface
        if async_mode:
            try:
                from ai_interface.models import AIAgent
                
                # Получаем ContentType для модели
                content_type = ContentType.objects.get_for_model(model_instance)
                
                # Получаем домен
                site = get_current_site(request)
                domain = site.domain if site else None
                
                # Формируем дополнительные данные
                additional_data = {}
                if additional_prompt:
                    additional_data['additional_prompt'] = additional_prompt
                
                # Получаем агент из генератора (если не указан, используется AILENGO из настроек)
                agent = generator.agent
                
                # Создаем задачу через адаптер
                task = create_generation_task(
                    prompt_version=prompt_version,
                    content_type=content_type,
                    object_id=int(model_id),
                    action=action,
                    additional_data=additional_data if additional_data else None,
                    agent=agent,  # Используем агент из ContentGenerator или AILENGO из настроек
                    domain=domain
                )
                
                return JsonResponse({
                    'status': 'ok',
                    'task_id': task.id,
                    'message': 'Задача создана и отправлена в AI-агент'
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
    # Получаем метод модели через рефлексию
    method = getattr(model_instance, action)
    
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


@login_required()
def get_actions(request):
    """
    API endpoint для получения списка действий (actions) по generator_id.
    
    Параметры:
        - generator_id (int): ID генератора контента
    
    Возвращает:
        JSON: {
            "status": "ok",
            "actions": [
                {"name": "set_seo_params", "label": "Сгенерировать SEO параметры", "icon": "🔍"},
                ...
            ]
        } или {"status": "error", "message": "Генератор не найден"} с кодом 404
    """
    try:
        generator_id = request.GET.get('generator_id')
        
        # Валидация
        if not generator_id:
            return JsonResponse({
                'status': 'error',
                'message': 'Отсутствует обязательный параметр: generator_id'
            }, status=400)
        
        try:
            generator_id = int(generator_id)
        except (ValueError, TypeError):
            return JsonResponse({
                'status': 'error',
                'message': 'generator_id должен быть числом'
            }, status=400)
        
        # Получаем генератор
        from content_generator.models import ContentGenerator
        try:
            generator = ContentGenerator.objects.get(id=generator_id)
        except ContentGenerator.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Генератор не найден'
            }, status=404)
        
        # Получаем действия генератора
        actions = generator.actions.all()
        
        # Формируем массив действий
        actions_list = [
            {
                'name': action.name,
                'label': action.label,
                'icon': action.icon
            }
            for action in actions
        ]
        
        return JsonResponse({
            'status': 'ok',
            'actions': actions_list
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        }, status=500)
