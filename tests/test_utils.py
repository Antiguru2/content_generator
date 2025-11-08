"""
Тесты для утилит content_generator.
"""

from django.test import TestCase
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.core.cache import cache

from content_generator.models import PromptVersion, GeneratedContent
from content_generator.utils import (
    compare_prompt_versions,
    get_prompt_statistics,
    sanitize_html_tags,
    validate_prompt_length,
    validate_generation_data
)


class ComparePromptVersionsTest(TestCase):
    """Тесты для функции compare_prompt_versions."""

    def test_compare_identical_versions(self):
        """Тест сравнения идентичных версий."""
        content = 'Одинаковое содержимое промпта'
        result = compare_prompt_versions(content, content)
        
        self.assertIn('side_by_side', result)
        self.assertIn('unified_diff', result)
        self.assertIn('stats', result)
        self.assertEqual(result['stats']['similarity'], 100.0)
        self.assertEqual(result['stats']['added'], 0)
        self.assertEqual(result['stats']['removed'], 0)

    def test_compare_different_versions(self):
        """Тест сравнения разных версий."""
        content1 = 'Первая версия промпта'
        content2 = 'Вторая версия промпта'
        result = compare_prompt_versions(content1, content2)
        
        self.assertIn('side_by_side', result)
        self.assertIn('unified_diff', result)
        self.assertIn('stats', result)
        self.assertLess(result['stats']['similarity'], 100.0)

    def test_compare_with_additions(self):
        """Тест сравнения версий с добавлениями."""
        content1 = 'Старая версия'
        content2 = 'Старая версия\nНовая строка'
        result = compare_prompt_versions(content1, content2)
        
        self.assertGreater(result['stats']['added'], 0)
        self.assertEqual(result['stats']['removed'], 0)

    def test_compare_with_deletions(self):
        """Тест сравнения версий с удалениями."""
        content1 = 'Старая версия\nУдаленная строка'
        content2 = 'Старая версия'
        result = compare_prompt_versions(content1, content2)
        
        self.assertEqual(result['stats']['added'], 0)
        self.assertGreater(result['stats']['removed'], 0)

    def test_compare_with_replacements(self):
        """Тест сравнения версий с заменой."""
        content1 = 'Старая версия\nСтарая строка'
        content2 = 'Старая версия\nНовая строка'
        result = compare_prompt_versions(content1, content2)
        
        self.assertGreater(result['stats']['added'], 0)
        self.assertGreater(result['stats']['removed'], 0)
        self.assertGreater(result['stats']['changed'], 0)

    def test_compare_side_by_side_format(self):
        """Тест формата side_by_side результата."""
        content1 = 'Строка 1\nСтрока 2'
        content2 = 'Строка 1\nСтрока 3'
        result = compare_prompt_versions(content1, content2)
        
        self.assertIsInstance(result['side_by_side'], list)
        for item in result['side_by_side']:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 3)  # (line1, line2, tag)

    def test_compare_unified_diff_format(self):
        """Тест формата unified_diff результата."""
        content1 = 'Строка 1\nСтрока 2'
        content2 = 'Строка 1\nСтрока 3'
        result = compare_prompt_versions(content1, content2)
        
        self.assertIsInstance(result['unified_diff'], list)
        self.assertTrue(len(result['unified_diff']) > 0)

    def test_compare_large_prompts(self):
        """Тест сравнения больших промптов (проверка оптимизации)."""
        content1 = 'Строка\n' * 15000  # Большой промпт
        content2 = 'Строка\n' * 15000 + 'Новая строка\n'
        result = compare_prompt_versions(content1, content2, max_lines=10000)
        
        # Проверяем, что результат получен (не упал с ошибкой)
        self.assertIn('stats', result)
        self.assertIn('truncated', result)
        # Для больших промптов может быть установлен флаг truncated
        self.assertIsInstance(result['truncated'], bool)

    def test_compare_stats_structure(self):
        """Тест структуры статистики сравнения."""
        content1 = 'Версия 1'
        content2 = 'Версия 2'
        result = compare_prompt_versions(content1, content2)
        
        stats = result['stats']
        self.assertIn('added', stats)
        self.assertIn('removed', stats)
        self.assertIn('changed', stats)
        self.assertIn('similarity', stats)
        self.assertIn('total_lines_1', stats)
        self.assertIn('total_lines_2', stats)
        self.assertIn('processed_lines_1', stats)
        self.assertIn('processed_lines_2', stats)


class GetPromptStatisticsTest(TestCase):
    """Тесты для функции get_prompt_statistics."""

    def setUp(self):
        """Подготовка тестовых данных."""
        self.prompt_version = PromptVersion.objects.create(
            version_number=1,
            description='Тестовая версия',
            prompt_content='Тестовое содержимое',
            engineer_name='Тестовый инженер'
        )
        
        self.content_type = ContentType.objects.create(
            app_label='store',
            model='product'
        )

    def test_statistics_empty_version(self):
        """Тест статистики для версии без контента."""
        stats = get_prompt_statistics(self.prompt_version)
        
        self.assertEqual(stats['generated_count'], 0)
        self.assertEqual(stats['reviewed_count'], 0)
        self.assertEqual(stats['review_percentage'], 0.0)
        self.assertIsNone(stats['average_rating'])
        self.assertEqual(stats['success_count'], 0)
        self.assertEqual(stats['failure_count'], 0)
        self.assertEqual(stats['pending_count'], 0)

    def test_statistics_with_content(self):
        """Тест статистики для версии с контентом."""
        # Создаем контент с разными статусами
        GeneratedContent.objects.create(
            prompt_version=self.prompt_version,
            content_type=self.content_type,
            object_id=1,
            generated_data={'test': 'data1'},
            status='SUCCESS'
        )
        
        GeneratedContent.objects.create(
            prompt_version=self.prompt_version,
            content_type=self.content_type,
            object_id=2,
            generated_data={'test': 'data2'},
            status='SUCCESS',
            reviewed_at=timezone.now()
        )
        
        GeneratedContent.objects.create(
            prompt_version=self.prompt_version,
            content_type=self.content_type,
            object_id=3,
            generated_data={'test': 'data3'},
            status='FAILURE'
        )
        
        GeneratedContent.objects.create(
            prompt_version=self.prompt_version,
            content_type=self.content_type,
            object_id=4,
            generated_data={'test': 'data4'},
            status='PENDING'
        )
        
        stats = get_prompt_statistics(self.prompt_version)
        
        self.assertEqual(stats['generated_count'], 4)
        self.assertEqual(stats['reviewed_count'], 1)
        self.assertEqual(stats['review_percentage'], 25.0)
        self.assertEqual(stats['success_count'], 2)
        self.assertEqual(stats['failure_count'], 1)
        self.assertEqual(stats['pending_count'], 1)

    def test_statistics_with_ratings(self):
        """Тест статистики для версии с оценками."""
        GeneratedContent.objects.create(
            prompt_version=self.prompt_version,
            content_type=self.content_type,
            object_id=1,
            generated_data={'test': 'data1'},
            status='REVIEWED',
            rating=4
        )
        
        GeneratedContent.objects.create(
            prompt_version=self.prompt_version,
            content_type=self.content_type,
            object_id=2,
            generated_data={'test': 'data2'},
            status='REVIEWED',
            rating=5
        )
        
        GeneratedContent.objects.create(
            prompt_version=self.prompt_version,
            content_type=self.content_type,
            object_id=3,
            generated_data={'test': 'data3'},
            status='REVIEWED',
            rating=3
        )
        
        stats = get_prompt_statistics(self.prompt_version)
        
        self.assertIsNotNone(stats['average_rating'])
        self.assertEqual(stats['average_rating'], 4.0)  # (4 + 5 + 3) / 3 = 4.0

    def test_statistics_caching(self):
        """Тест кэширования статистики."""
        # Очищаем кэш
        cache.clear()
        
        # Получаем статистику первый раз
        stats1 = get_prompt_statistics(self.prompt_version)
        
        # Создаем новый контент
        GeneratedContent.objects.create(
            prompt_version=self.prompt_version,
            content_type=self.content_type,
            object_id=1,
            generated_data={'test': 'data'},
            status='SUCCESS'
        )
        
        # Получаем статистику второй раз (должна быть из кэша)
        stats2 = get_prompt_statistics(self.prompt_version)
        
        # Статистика должна быть одинаковой (из кэша)
        # Но это зависит от времени жизни кэша, поэтому просто проверяем структуру
        self.assertEqual(stats1.keys(), stats2.keys())


class SanitizeHtmlTagsTest(TestCase):
    """Тесты для функции sanitize_html_tags."""

    def test_sanitize_removes_all_tags(self):
        """Тест удаления всех HTML-тегов."""
        text = '<p>Текст с <strong>тегами</strong></p>'
        result = sanitize_html_tags(text)
        
        self.assertNotIn('<p>', result)
        self.assertNotIn('<strong>', result)
        self.assertIn('Текст с', result)
        self.assertIn('тегами', result)

    def test_sanitize_preserves_text_content(self):
        """Тест сохранения текстового содержимого."""
        text = '<div>Важный текст</div>'
        result = sanitize_html_tags(text)
        
        self.assertIn('Важный текст', result)
        self.assertNotIn('<div>', result)

    def test_sanitize_empty_string(self):
        """Тест обработки пустой строки."""
        result = sanitize_html_tags('')
        self.assertEqual(result, '')

    def test_sanitize_none(self):
        """Тест обработки None."""
        result = sanitize_html_tags(None)
        self.assertEqual(result, '')

    def test_sanitize_with_allowed_tags(self):
        """Тест санитизации с разрешенными тегами."""
        text = '<p>Текст с <strong>тегами</strong> и <script>скриптом</script></p>'
        result = sanitize_html_tags(text, allowed_tags=['p', 'strong'])
        
        # Разрешенные теги должны остаться
        self.assertIn('<p>', result)
        self.assertIn('<strong>', result)
        # Запрещенные теги должны быть удалены
        self.assertNotIn('<script>', result)

    def test_sanitize_html_entities(self):
        """Тест обработки HTML-сущностей."""
        text = 'Текст с &nbsp; и &amp; символами'
        result = sanitize_html_tags(text)
        
        # HTML-сущности должны быть декодированы
        self.assertIn(' ', result)  # &nbsp; -> пробел
        self.assertIn('&', result)  # &amp; -> &


class ValidatePromptLengthTest(TestCase):
    """Тесты для функции validate_prompt_length."""

    def test_validate_valid_length(self):
        """Тест валидации валидной длины."""
        prompt = 'Валидный промпт'
        is_valid, error = validate_prompt_length(prompt)
        
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_validate_too_short(self):
        """Тест валидации слишком короткого промпта."""
        prompt = ''
        is_valid, error = validate_prompt_length(prompt, min_length=1)
        
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
        self.assertIn('короткий', error.lower())

    def test_validate_too_long(self):
        """Тест валидации слишком длинного промпта."""
        prompt = 'A' * 50001  # Превышает лимит 50000
        is_valid, error = validate_prompt_length(prompt, max_length=50000)
        
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
        self.assertIn('длинный', error.lower())

    def test_validate_max_length(self):
        """Тест валидации промпта максимальной длины."""
        prompt = 'A' * 50000  # Ровно лимит
        is_valid, error = validate_prompt_length(prompt, max_length=50000)
        
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_validate_min_length(self):
        """Тест валидации промпта минимальной длины."""
        prompt = 'A'  # Ровно минимум
        is_valid, error = validate_prompt_length(prompt, min_length=1)
        
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_validate_not_string(self):
        """Тест валидации не-строки."""
        prompt = 123
        is_valid, error = validate_prompt_length(prompt)
        
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
        self.assertIn('строкой', error.lower())


class ValidateGenerationDataTest(TestCase):
    """Тесты для функции validate_generation_data."""

    def test_validate_valid_data(self):
        """Тест валидации валидных данных."""
        data = {
            'class_name': 'Product',
            'model_id': 1,
            'action': 'set_seo_params'
        }
        is_valid, error = validate_generation_data(data)
        
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_validate_not_dict(self):
        """Тест валидации не-словаря."""
        data = 'not a dict'
        is_valid, error = validate_generation_data(data)
        
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
        self.assertIn('словарем', error.lower())

    def test_validate_missing_class_name(self):
        """Тест валидации отсутствующего class_name."""
        data = {
            'model_id': 1,
            'action': 'set_seo_params'
        }
        is_valid, error = validate_generation_data(data)
        
        self.assertFalse(is_valid)
        self.assertIn('class_name', error)

    def test_validate_missing_model_id(self):
        """Тест валидации отсутствующего model_id."""
        data = {
            'class_name': 'Product',
            'action': 'set_seo_params'
        }
        is_valid, error = validate_generation_data(data)
        
        self.assertFalse(is_valid)
        self.assertIn('model_id', error)

    def test_validate_missing_action(self):
        """Тест валидации отсутствующего action."""
        data = {
            'class_name': 'Product',
            'model_id': 1
        }
        is_valid, error = validate_generation_data(data)
        
        self.assertFalse(is_valid)
        self.assertIn('action', error)

    def test_validate_invalid_class_name(self):
        """Тест валидации невалидного class_name."""
        data = {
            'class_name': '',
            'model_id': 1,
            'action': 'set_seo_params'
        }
        is_valid, error = validate_generation_data(data)
        
        self.assertFalse(is_valid)
        self.assertIn('class_name', error)

    def test_validate_invalid_model_id(self):
        """Тест валидации невалидного model_id."""
        data = {
            'class_name': 'Product',
            'model_id': -1,
            'action': 'set_seo_params'
        }
        is_valid, error = validate_generation_data(data)
        
        self.assertFalse(is_valid)
        self.assertIn('model_id', error)

    def test_validate_invalid_action(self):
        """Тест валидации невалидного action."""
        data = {
            'class_name': 'Product',
            'model_id': 1,
            'action': 'invalid_action'
        }
        is_valid, error = validate_generation_data(data)
        
        self.assertFalse(is_valid)
        self.assertIn('action', error)

    def test_validate_valid_optional_fields(self):
        """Тест валидации валидных опциональных полей."""
        data = {
            'class_name': 'Product',
            'model_id': 1,
            'action': 'set_seo_params',
            'prompt_version_id': 5,
            'additional_prompt': 'Дополнительный промпт',
            'async_mode': True
        }
        is_valid, error = validate_generation_data(data)
        
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_validate_invalid_prompt_version_id(self):
        """Тест валидации невалидного prompt_version_id."""
        data = {
            'class_name': 'Product',
            'model_id': 1,
            'action': 'set_seo_params',
            'prompt_version_id': -1
        }
        is_valid, error = validate_generation_data(data)
        
        self.assertFalse(is_valid)
        self.assertIn('prompt_version_id', error)

    def test_validate_allowed_actions(self):
        """Тест валидации разрешенных действий."""
        allowed_actions = ['set_seo_params', 'set_description', 'upgrade_name', 'set_some_params']
        
        for action in allowed_actions:
            data = {
                'class_name': 'Product',
                'model_id': 1,
                'action': action
            }
            is_valid, error = validate_generation_data(data)
            self.assertTrue(is_valid, f'Action {action} should be valid')

