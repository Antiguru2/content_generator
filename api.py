import traceback
import threading

from django.apps import apps
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, HttpResponse


# Словарь для маппинга действий на методы
ACTION_METHODS = {
    'set_seo_params': 'set_seo_params',
    'set_description': 'set_description', 
    'upgrade_name': 'upgrade_name',
    'set_some_params': 'set_some_params',
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
        - additional_prompt (str, optional): Дополнительный промпт от пользователя
        - async_mode (bool, optional): Выполнять асинхронно (по умолчанию False)
    
    Возвращает:
        JSON: { "status": "ok", "task_id": <id> } или { "status": "error", "message": <error> }
    """
    try:
        # Получаем параметры
        class_name = request.GET.get('class_name')
        model_id = request.GET.get('model_id')
        action = request.GET.get('action')
        additional_prompt = request.GET.get('additional_prompt', '')
        async_mode = request.GET.get('async_mode', 'false').lower() == 'true'
        
        # Валидация
        if not class_name or not model_id or not action:
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
            Model = apps.get_model('store', class_name)
            model_instance = get_object_or_404(Model, id=model_id)
        except LookupError:
            return JsonResponse({
                'status': 'error',
                'message': f'Модель {class_name} не найдена'
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
                'message': f'Модель {class_name} не поддерживает действие {action}'
            }, status=400)
        
        # Если асинхронный режим - создаем задачу через ai_interface
        if async_mode:
            try:
                from ai_interface.models import AITask
                
                # Создаем задачу
                task = AITask.objects.create(
                    agent_name=f'content_generator_{action}',
                    data={
                        'class_name': class_name,
                        'model_id': model_id,
                        'action': action,
                        'additional_prompt': additional_prompt,
                    },
                    status='PENDING'
                )
                
                # Запускаем выполнение в фоновом потоке
                def execute_task():
                    try:
                        execute_generation_action(
                            model_instance, 
                            action, 
                            additional_prompt
                        )
                        task.status = 'SUCCESS'
                        task.result = {'success': True}
                        task.save()
                    except Exception as e:
                        task.status = 'FAILURE'
                        task.result = {'error': str(e), 'traceback': traceback.format_exc()}
                        task.save()
                
                thread = threading.Thread(target=execute_task)
                thread.daemon = True
                thread.start()
                
                return JsonResponse({
                    'status': 'ok',
                    'task_id': task.id,
                    'message': 'Задача создана и выполняется'
                })
                
            except ImportError:
                # Если ai_interface недоступен, выполняем синхронно
                pass
        
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
    
    Args:
        model_instance: Экземпляр модели
        action: Название действия
        additional_prompt: Дополнительный промпт
    """
    method_name = ACTION_METHODS[action]
    method = getattr(model_instance, method_name)
    
    # Для действий, поддерживающих дополнительный промпт
    if action in ['set_some_params'] and additional_prompt:
        method(additional_prompt)
    else:
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
