"""
Сигналы для интеграции с внешними модулями.
"""

from django.dispatch import receiver
from django.db.models.signals import post_save, post_migrate

from content_generator.models import Action
from ai_interface.actions import register_postprocessor
from content_generator.utils import process_generation_result

# ========== ПОДСИСТЕМА INTEGRATION ==========

def process_content_generation_result(ai_task):
    """
    Постпроцессор для обработки результатов генерации контента.
    
    Регистрируется для всех агентов content_generator_* и обрабатывает
    результаты генерации, создавая/обновляя GeneratedContent и связывая
    его с PromptVersion.
    
    Args:
        ai_task: Экземпляр AITask из ai_interface с результатом генерации
    """
    
    # Обрабатываем результат только для задач content_generator
    if ai_task.endpoint.startswith('content_generator_'):
        result = process_generation_result(ai_task)
        if result and result.get('status') == 'error':
            print(f'Error processing generation result: {result.get("message")}')


# Регистрируем постпроцессор для всех агентов content_generator
# Используем общий паттерн для всех действий генерации
register_postprocessor('content_generator_set_seo_params', process_content_generation_result)
register_postprocessor('content_generator_set_description', process_content_generation_result)
register_postprocessor('content_generator_upgrade_name', process_content_generation_result)
register_postprocessor('content_generator_set_some_params', process_content_generation_result)


ACTIONS = [
    { 
        'name': 'set_seo_params', 
        'label': 'SEO параметры', 
        'icon': '🔍'
    },
    { 
        'name': 'set_description', 
        'label': 'Полное описание', 
        'icon': '📝'
    },
    { 
        'name': 'upgrade_name', 
        'label': 'Улучшить название', 
        'icon': '✨'
    },
    { 
        'name': 'change_img', 
        'label': 'Выбрать картинку', 
        'icon': '🖼️'
    },
    { 
        'name': 'set_some_params', 
        'label': 'Улучшить SEO и description', 
        'icon': '🚀'
    },
    { 
        'name': 'update_html_constructor', 
        'label': 'Улучшить шаблон страницы', 
        'icon': '🎨'
    }                    
]


@receiver(post_migrate)
def create_actions_from_settings(sender, **kwargs):
    """
    Создает записи Action из настроек при миграции.
    
    Автоматически создает действия для генерации контента на основе
    списка ACTIONS из settings.py при выполнении миграций.
    """
    if sender.name == 'content_generator':
        for action_data in ACTIONS:
            Action.objects.get_or_create(
                name=action_data['name'],
                defaults={
                    'label': action_data['label'],
                    'icon': action_data['icon'],
                }
            )
