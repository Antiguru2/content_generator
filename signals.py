"""
Сигналы для интеграции с внешними модулями.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from ai_interface.actions import register_postprocessor


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
    from content_generator.utils import process_generation_result
    
    # Обрабатываем результат только для задач content_generator
    if ai_task.agent_name.startswith('content_generator_'):
        result = process_generation_result(ai_task)
        if result and result.get('status') == 'error':
            print(f'Error processing generation result: {result.get("message")}')


# Регистрируем постпроцессор для всех агентов content_generator
# Используем общий паттерн для всех действий генерации
register_postprocessor('content_generator_set_seo_params', process_content_generation_result)
register_postprocessor('content_generator_set_description', process_content_generation_result)
register_postprocessor('content_generator_upgrade_name', process_content_generation_result)
register_postprocessor('content_generator_set_some_params', process_content_generation_result)
