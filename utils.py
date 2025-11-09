import re 
import bs4 
import json
import requests
import difflib
from typing import Dict, List, Tuple, Any, Optional, Union

from django.db import models
from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache

from bs4 import (
    BeautifulSoup,
    Tag,
)

from super_requester.models import SuperRequester
from main.models import SitePreferences
from super_requester.utils import send_message_about_error


super_requester = SuperRequester()

url_to_get_seo_params = getattr(settings, 'URL_TO_GET_SEO_PARAMS', None)
url_to_description_for_product = getattr(settings, 'URL_TO_DESCRIPTION_FOR_PRODUCT', None)
url_to_description_for_category = getattr(settings, 'URL_TO_DESCRIPTION_FOR_CATEGORY', None)
url_to_upgrade_name = getattr(settings, 'URL_TO_UPDATE_NAME', None)

url_to_set_some_params_for_product = getattr(settings, 'URL_TO_SET_TO_SOME_PARAMS_FOR_PRODUCT', None)
url_to_set_some_params_for_category = getattr(settings, 'URL_TO_SET_TO_SOME_PARAMS_FOR_CATEGORY', None)


def set_seo_params_of_model(model):
    """Генерирует SEO параметры для модели"""
    # print('set_seo_params_of_model')
    if not url_to_get_seo_params:
        print('Урл для получения сео параметров, НЕ УСТАНОВЛЕН')
        return
    
    description = model.description
    if not description:
        description = get_text_from_html(model.get_temporary_info_value())

    if len(description) > 317:
        description = description[:317]    

    data = {
        'name': model.name,
        'description': description
    }     
    # print('data', data)
    response = super_requester.get_response(
        url_to_get_seo_params, 
        method='POST',
        data=data
    )        

    try:
        response_data = json.loads(response.text)
        # print('response_data', response_data)
    except json.decoder.JSONDecodeError:
        send_message_about_error(
            'json.decoder.JSONDecodeError',
            'set_seo_params_of_model',
            error_data=f'Пришло {response.text}'
        )
        print('json.decoder.JSONDecodeError')
        return
    try:          
        seo_parameters = model.seo_parameters.super_object
        seo_parameters.title = response_data.get('title')
        seo_parameters.description = response_data.get('description')
        seo_parameters.save()         
    except:
        SEOParameters: models.Model = apps.get_model('seo_parameters', 'SEOParameters') 
        seo_parameters = SEOParameters.objects.create(
            content_type=ContentType.objects.get_for_model(model),
            object_id=model.id,
            title=response_data.get('title'),
            description=response_data.get('description'),
        )
               

def set_description_of_model(model, description=''): 
    """Генерирует описание для модели"""
    print('set_description_of_model')
    # print('model', model)
    description = model.get_temporary_info_value()
    if not description:
        print('temporary_info_value не получен')
        # return        

    name_model = model.__class__.__name__.lower()
    print('name_model', name_model)
    if name_model == 'category': 
        company_name = ''
        url_to_description = url_to_description_for_category

        if hasattr(model, 'site') and model.site and hasattr(model.site, 'preferences') and model.site.preferences and model.site.preferences.company_name:
            company_name = model.site.preferences.company_name
        else: 
            site_preferences = SitePreferences.get_model()
            company_name = getattr(site_preferences, 'company_name', '')

        data = {
            'company_profile': company_name,
            'category': model.name,
            'category_description': description,
        }        

    if name_model == 'product': 
        url_to_description = url_to_description_for_product
        data = {
            'category_name': model.category.name,
            'name': model.name,
            'description': description,
            'characteristics': model.all_attributs_data_as_str,
        }        
    print('data', data)
    if not url_to_description:
        print('Урл для получения description, НЕ УСТАНОВЛЕН')
        send_message_about_error(
            'Урл для получения description, НЕ УСТАНОВЛЕН',
            'main utils set_description_of_model',
            to_fix=True,
        )
        return
    
    response = super_requester.get_response(
        url_to_description, 
        method='POST',
        data=data
    )  
    print('statuse_code', response.status_code)
    if response and response.text:
        description = response.text
        print('description', description)
        try:
            data = json.loads(response.content)
            description = data.get('description_html', description)
        except json.decoder.JSONDecodeError:
            print('description')
            print('statuse_code', response.status_code)

            pass
        model.description = description
        model.save()       


def upgrade_name_of_model(model):
    """Улучшает название модели"""
    name_model = model.__class__.__name__.lower()
    if name_model == 'product':
        # print(' model.name',  model.name)
        # print('model.category.name', model.category.name)
        # print('model.all_attributs_data_as_str', model.all_attributs_data_as_str)
        data = {
            'name': model.name, 
            'category': model.category.name, 
            'attributes': model.all_attributs_data_as_str,
        }      
        response = super_requester.get_response(
            url_to_upgrade_name, 
            method='POST',
            data=data
        ) 
        
        new_name = response.text
        try:
            response_data = json.loads(response.text)
            # print('response_data', response_data)
            new_name = response_data.get('new_name')
        except json.decoder.JSONDecodeError:
            pass

        # print('new_name', new_name)
        model.name = new_name
        model.save()                        

def set_some_params_of_model(model, additional_prompt=None):
    """Комплексное улучшение параметров модели"""
    # print('set_some_params')
    company_name = ''
    if hasattr(model, 'site') and model.site and hasattr(model.site, 'preferences') and model.site.preferences:
        site_preferences = model.site.preferences
    else: 
        site_preferences = SitePreferences.get_model()

    name_model = model._meta.model_name
    if name_model == 'product':
        url_to_set_some_params = url_to_set_some_params_for_product
        category_name = ''
        if model.category and model.category.name:
            category_name = model.category.name

        data = {
            'company_name': getattr(site_preferences, 'company_name', ''),
            'company_profile': getattr(site_preferences, 'company_profile', ''),
            'product_name': model.name,
            'category_name': category_name,
            'product_attributes': model.all_attributs_data_as_str,
            'additional_prompt': additional_prompt,
        }   
    elif name_model == 'category':
        url_to_set_some_params = url_to_set_some_params_for_category
        data = {
            'category_name': model.name,
            'category_attributes': model.get_category_attributes_as_str(),
            'company_name': getattr(site_preferences, 'company_name', ''),
        }     

    if not url_to_set_some_params:
        print('Урл для получения set_some_params, НЕ УСТАНОВЛЕН')
        return
    
    response = super_requester.get_response(
        url_to_set_some_params, 
        method='POST',
        data=data
    )        

    try:
        response_data = json.loads(response.text)
        # print('response_data', response_data)
    except json.decoder.JSONDecodeError:
        send_message_about_error(
            'json.decoder.JSONDecodeError',
            'set_seo_params_of_model',
            error_data=f'Пришло {response.text}'
        )
        print('json.decoder.JSONDecodeError')
        return
    print('response_data', response_data)
    
    model.description = response_data.get('description', model.description)
    model.name = response_data.get('new_name', model.name)
    model.save()

    try:          
        seo_parameters = model.seo_parameters.super_object
        seo_parameters.title = response_data.get('title')
        seo_parameters.description = response_data.get('description')
        seo_parameters.save()         
    except:
        SEOParameters: models.Model = apps.get_model('seo_parameters', 'SEOParameters') 
        seo_parameters = SEOParameters.objects.create(
            content_type=ContentType.objects.get_for_model(model),
            object_id=model.id,
            title=response_data.get('title'),
            description=response_data.get('description'),
        )
            

def get_additional_header_elements():
    """Возвращает дополнительные элементы для заголовка"""
    result = None
    return result
        

def get_model_by_name(model_name: str) -> Optional[models.Model]:
    """Получает модель по имени"""
    try:
        return apps.get_model('store', model_name)
    except LookupError:
        return None


# ========== ПОДСИСТЕМА PROMPTS ==========

def compare_prompt_versions(content1: str, content2: str, max_lines: int = 10000) -> Dict[str, Any]:
    """
    Сравнивает две версии промпта и возвращает структурированные данные для отображения.
    
    Использует difflib для поиска различий между версиями промптов.
    Подсчитывает статистику изменений (добавления, удаления, похожесть).
    Оптимизировано для больших промптов: ограничивает обработку при превышении max_lines.
    
    Args:
        content1: Содержимое первой версии промпта
        content2: Содержимое второй версии промпта
        max_lines: Максимальное количество строк для обработки (по умолчанию 10000)
    
    Returns:
        Словарь с ключами:
        - 'side_by_side': список кортежей (line1, line2, tag) для режима Side-by-Side
        - 'unified_diff': список строк для режима Unified Diff
        - 'stats': словарь со статистикой (added, removed, changed, similarity)
        - 'truncated': флаг, указывающий, были ли данные обрезаны
    """
    # Разбиваем тексты на строки для сравнения (без keepends для чистоты)
    lines1 = content1.splitlines(keepends=False)
    lines2 = content2.splitlines(keepends=False)
    
    # Оптимизация для больших промптов: ограничиваем обработку
    # Сохраняем оригинальные размеры для статистики
    truncated = False
    original_lines1_count = len(lines1)
    original_lines2_count = len(lines2)
    
    # Если промпты слишком большие, обрезаем их для ускорения обработки
    # Это позволяет обрабатывать очень большие промпты без зависания
    if len(lines1) > max_lines or len(lines2) > max_lines:
        truncated = True
        # Для больших промптов используем только первые max_lines строк
        # Это компромисс между точностью и производительностью
        lines1 = lines1[:max_lines]
        lines2 = lines2[:max_lines]
        # Пересоздаем содержимое для подсчета похожести
        # (нужно для SequenceMatcher, который работает со строками)
        content1_truncated = '\n'.join(lines1)
        content2_truncated = '\n'.join(lines2)
    else:
        # Для небольших промптов используем оригинальное содержимое
        content1_truncated = content1
        content2_truncated = content2
    
    # Используем SequenceMatcher для подсчета похожести
    # Для очень больших текстов (более 100000 символов) используем быстрый режим
    # с игнорированием пробелов и табов для ускорения
    if len(content1_truncated) + len(content2_truncated) > 100000:
        # Используем isjunk для ускорения на больших текстах
        # Игнорируем пробелы и табы, так как они не влияют на смысл при сравнении
        matcher = difflib.SequenceMatcher(
            lambda x: x in ' \t',  # Игнорируем пробелы и табы
            content1_truncated,
            content2_truncated
        )
    else:
        # Для небольших текстов используем полное сравнение без оптимизаций
        matcher = difflib.SequenceMatcher(None, content1_truncated, content2_truncated)
    
    similarity = matcher.ratio() * 100
    
    # Создаем diff для режима Side-by-Side
    # Структура: список кортежей (line1, line2, tag), где:
    # - line1: строка из первой версии (или пустая строка)
    # - line2: строка из второй версии (или пустая строка)
    # - tag: тип изменения ('equal', 'delete', 'insert', 'replace')
    side_by_side = []
    
    # Обрабатываем opcodes для создания side-by-side представления
    # opcodes - это список кортежей (tag, i1, i2, j1, j2), описывающих изменения:
    # - tag: тип изменения ('equal', 'delete', 'insert', 'replace')
    # - i1, i2: индексы строк в первой версии
    # - j1, j2: индексы строк во второй версии
    opcodes = difflib.SequenceMatcher(None, lines1, lines2).get_opcodes()
    
    # Обрабатываем каждый opcode для построения side-by-side представления
    for tag, i1, i2, j1, j2 in opcodes:
        if tag == 'equal':
            # Одинаковые строки - показываем в обеих колонках
            for i in range(i1, i2):
                if i < len(lines1):
                    side_by_side.append((lines1[i], lines1[i], 'equal'))
        elif tag == 'delete':
            # Удаленные строки - показываем только в первой колонке
            for i in range(i1, i2):
                if i < len(lines1):
                    side_by_side.append((lines1[i], '', 'delete'))
        elif tag == 'insert':
            # Добавленные строки - показываем только во второй колонке
            for j in range(j1, j2):
                if j < len(lines2):
                    side_by_side.append(('', lines2[j], 'insert'))
        elif tag == 'replace':
            # Замененные строки - показываем все удаленные, затем все добавленные
            # Это позволяет видеть полную картину изменений
            # Сначала удаленные строки (из первой версии)
            for i in range(i1, i2):
                if i < len(lines1):
                    side_by_side.append((lines1[i], '', 'delete'))
            # Затем добавленные строки (из второй версии)
            for j in range(j1, j2):
                if j < len(lines2):
                    side_by_side.append(('', lines2[j], 'insert'))
    
    # Создаем unified diff для отображения
    unified_diff_lines = list(difflib.unified_diff(
        lines1, lines2,
        fromfile='Версия 1',
        tofile='Версия 2',
        lineterm='',
        n=3
    ))
    
    # Подсчитываем статистику на основе opcodes
    added_count = sum(j2 - j1 for tag, i1, i2, j1, j2 in opcodes if tag in ('insert', 'replace'))
    removed_count = sum(i2 - i1 for tag, i1, i2, j1, j2 in opcodes if tag in ('delete', 'replace'))
    changed_count = sum(1 for tag, i1, i2, j1, j2 in opcodes if tag == 'replace')
    
    stats = {
        'added': added_count,
        'removed': removed_count,
        'changed': changed_count,
        'similarity': round(similarity, 2),
        'total_lines_1': original_lines1_count,
        'total_lines_2': original_lines2_count,
        'processed_lines_1': len(lines1),
        'processed_lines_2': len(lines2),
    }
    
    return {
        'side_by_side': side_by_side,
        'unified_diff': unified_diff_lines,
        'stats': stats,
        'truncated': truncated,
    }


def get_prompt_statistics(prompt_version) -> Dict[str, Any]:
    """
    Подсчитывает статистику использования версии промпта.
    
    Использует оптимизированные запросы к БД (aggregate, annotate) для подсчета метрик.
    Поддерживает кэширование результатов (опционально, через Django cache).
    
    Args:
        prompt_version: Экземпляр модели PromptVersion
    
    Returns:
        Словарь со статистикой:
        - 'generated_count': количество сгенерированного контента
        - 'reviewed_count': количество проверенного контента
        - 'review_percentage': процент проверенного контента
        - 'average_rating': средний рейтинг (если доступен)
        - 'success_count': количество успешных генераций
        - 'failure_count': количество неудачных генераций
        - 'pending_count': количество ожидающих генераций
    """
    # Проверяем кэш
    cache_key = f'prompt_statistics_{prompt_version.id}'
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    try:
        GeneratedContent = apps.get_model('content_generator', 'GeneratedContent')
        if not GeneratedContent:
            return {
                'generated_count': 0,
                'reviewed_count': 0,
                'review_percentage': 0.0,
                'average_rating': None,
                'success_count': 0,
                'failure_count': 0,
                'pending_count': 0,
            }
        
        # Оптимизированный запрос с использованием aggregate
        # Используем один запрос для подсчета всех метрик вместо множественных запросов
        # Это значительно ускоряет работу при большом количестве записей
        from django.db.models import Count, Avg, Q
        
        queryset = GeneratedContent.objects.filter(prompt_version=prompt_version)
        
        # Подсчитываем все метрики одним запросом с использованием aggregate
        # Каждая метрика вычисляется с помощью фильтров (Q objects) для точности
        stats = queryset.aggregate(
            generated_count=Count('id'),  # Общее количество записей
            reviewed_count=Count('id', filter=Q(reviewed_at__isnull=False)),  # Проверенные записи
            success_count=Count('id', filter=Q(status='SUCCESS')),  # Успешные генерации
            failure_count=Count('id', filter=Q(status='FAILURE')),  # Неудачные генерации
            pending_count=Count('id', filter=Q(status__in=['PENDING', 'PROCESSING'])),  # Ожидающие генерации
            average_rating=Avg('rating', filter=Q(rating__isnull=False)),  # Средний рейтинг (только для оцененных)
        )
        
        # Вычисляем процент проверенного контента
        generated_count = stats['generated_count'] or 0
        reviewed_count = stats['reviewed_count'] or 0
        review_percentage = round((reviewed_count / generated_count * 100), 2) if generated_count > 0 else 0.0
        
        result = {
            'generated_count': generated_count,
            'reviewed_count': reviewed_count,
            'review_percentage': review_percentage,
            'average_rating': round(stats['average_rating'], 2) if stats['average_rating'] is not None else None,
            'success_count': stats['success_count'] or 0,
            'failure_count': stats['failure_count'] or 0,
            'pending_count': stats['pending_count'] or 0,
        }
        
        # Кэшируем результат на 5 минут
        cache.set(cache_key, result, 300)
        
        return result
        
    except (LookupError, AttributeError) as e:
        # Если модель не найдена, возвращаем пустую статистику
        return {
            'generated_count': 0,
            'reviewed_count': 0,
            'review_percentage': 0.0,
            'average_rating': None,
            'success_count': 0,
            'failure_count': 0,
            'pending_count': 0,
        }


# ========== ПОДСИСТЕМА GENERATION ==========

def sanitize_html_tags(text: str, allowed_tags: Optional[List[str]] = None) -> str:
    """
    Санитизирует HTML-теги в тексте, удаляя опасные теги и оставляя только разрешенные.
    
    Args:
        text: Текст для санитизации
        allowed_tags: Список разрешенных HTML-тегов (по умолчанию None - удаляются все теги)
    
    Returns:
        Очищенный от HTML-тегов текст
    """
    if not text:
        return ''
    
    if allowed_tags is None:
        # Удаляем все HTML-теги
        # Используем BeautifulSoup для безопасного парсинга
        try:
            soup = BeautifulSoup(text, 'html.parser')
            # Получаем только текстовое содержимое
            return soup.get_text(separator=' ', strip=True)
        except Exception:
            # Если BeautifulSoup не справился, используем регулярное выражение
            # Безопасное удаление всех HTML-тегов
            text = re.sub(r'<[^>]+>', '', text)
            # Декодируем HTML-сущности
            text = text.replace('&nbsp;', ' ')
            text = text.replace('&amp;', '&')
            text = text.replace('&lt;', '<')
            text = text.replace('&gt;', '>')
            text = text.replace('&quot;', '"')
            text = text.replace('&#39;', "'")
            return text.strip()
    else:
        # Оставляем только разрешенные теги
        try:
            soup = BeautifulSoup(text, 'html.parser')
            # Удаляем все теги, кроме разрешенных
            for tag in soup.find_all(True):
                if tag.name not in allowed_tags:
                    tag.unwrap()  # Удаляем тег, но оставляем содержимое
            return str(soup)
        except Exception:
            # Fallback: используем регулярное выражение
            # Создаем паттерн для разрешенных тегов
            allowed_pattern = '|'.join(allowed_tags)
            # Удаляем все теги, кроме разрешенных
            text = re.sub(
                rf'<(?!\/?(?:{allowed_pattern})\b)[^>]+>',
                '',
                text,
                flags=re.IGNORECASE
            )
            return text.strip()


def validate_prompt_length(prompt_content: str, max_length: int = 50000, min_length: int = 1) -> Tuple[bool, Optional[str]]:
    """
    Валидирует длину промпта.
    
    Args:
        prompt_content: Содержимое промпта для валидации
        max_length: Максимальная допустимая длина (по умолчанию 50000)
        min_length: Минимальная допустимая длина (по умолчанию 1)
    
    Returns:
        Кортеж (is_valid, error_message):
        - is_valid: True, если длина валидна, False в противном случае
        - error_message: Сообщение об ошибке или None, если валидация прошла успешно
    """
    if not isinstance(prompt_content, str):
        return False, 'Промпт должен быть строкой'
    
    content_length = len(prompt_content)
    
    if content_length < min_length:
        return False, f'Промпт слишком короткий. Минимальная длина: {min_length} символов'
    
    if content_length > max_length:
        return False, f'Промпт слишком длинный. Максимальная длина: {max_length} символов. Текущая длина: {content_length}'
    
    return True, None


def validate_generation_data(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Валидирует формат данных для генерации контента.
    
    Проверяет наличие обязательных полей и корректность их типов.
    
    Args:
        data: Словарь с данными для генерации
    
    Returns:
        Кортеж (is_valid, error_message):
        - is_valid: True, если данные валидны, False в противном случае
        - error_message: Сообщение об ошибке или None, если валидация прошла успешно
    """
    if not isinstance(data, dict):
        return False, 'Данные должны быть словарем (dict)'
    
    # Проверяем обязательные поля
    required_fields = ['class_name', 'model_id', 'action']
    
    for field in required_fields:
        if field not in data:
            return False, f'Отсутствует обязательное поле: {field}'
    
    # Валидация class_name
    class_name = data.get('class_name')
    if not isinstance(class_name, str) or not class_name.strip():
        return False, 'Поле class_name должно быть непустой строкой'
    
    # Валидация model_id
    model_id = data.get('model_id')
    if not isinstance(model_id, (int, str)):
        return False, 'Поле model_id должно быть числом или строкой'
    
    try:
        model_id_int = int(model_id)
        if model_id_int <= 0:
            return False, 'Поле model_id должно быть положительным числом'
    except (ValueError, TypeError):
        return False, 'Поле model_id должно быть валидным числом'
    
    # Валидация action
    action = data.get('action')
    if not isinstance(action, str) or not action.strip():
        return False, 'Поле action должно быть непустой строкой'
    
    # Проверяем допустимые значения action
    allowed_actions = ['set_seo_params', 'set_description', 'upgrade_name', 'set_some_params']
    if action not in allowed_actions:
        return False, f'Поле action должно быть одним из: {", ".join(allowed_actions)}'
    
    # Валидация опциональных полей
    if 'prompt_version_id' in data:
        prompt_version_id = data.get('prompt_version_id')
        if prompt_version_id is not None:
            try:
                prompt_version_id_int = int(prompt_version_id)
                if prompt_version_id_int <= 0:
                    return False, 'Поле prompt_version_id должно быть положительным числом'
            except (ValueError, TypeError):
                return False, 'Поле prompt_version_id должно быть валидным числом или None'
    
    if 'additional_prompt' in data:
        additional_prompt = data.get('additional_prompt')
        if additional_prompt is not None and not isinstance(additional_prompt, str):
            return False, 'Поле additional_prompt должно быть строкой или None'
    
    if 'async_mode' in data:
        async_mode = data.get('async_mode')
        if not isinstance(async_mode, bool):
            return False, 'Поле async_mode должно быть булевым значением'
    
    return True, None


def process_generation_result(ai_task) -> Optional[Dict[str, Any]]:
    """
    Обрабатывает результат генерации от ai_interface.
    
    Использует ai_interface_adapter для создания/обновления GeneratedContent
    и связывания его с PromptVersion.
    
    Args:
        ai_task: Экземпляр AITask из ai_interface с результатом генерации
    
    Returns:
        Словарь с информацией о результате обработки или None при ошибке
    """
    from content_generator.ai_interface_adapter import process_generation_result as process_result
    
    try:
        generated_content = process_result(ai_task)
        if generated_content:
            return {
                'status': 'success',
                'generated_content_id': generated_content.id,
                'prompt_version_id': generated_content.prompt_version.id if generated_content.prompt_version else None,
            }
        else:
            return {
                'status': 'error',
                'message': 'Failed to process generation result'
            }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'status': 'error',
            'message': str(e)
        }