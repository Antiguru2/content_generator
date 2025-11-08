"""
Тесты для моделей content_generator.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import timedelta

from content_generator.models import PromptVersion, GeneratedContent

User = get_user_model()


class PromptVersionModelTest(TestCase):
    """Тесты для модели PromptVersion."""

    def setUp(self):
        """Подготовка тестовых данных."""
        self.engineer_name = 'Иван Иванов'
        self.description = 'Тестовое описание версии'
        self.prompt_content = 'Тестовое содержимое промпта'

    def test_create_prompt_version(self):
        """Тест создания PromptVersion."""
        version = PromptVersion.objects.create(
            version_number=1,
            description=self.description,
            prompt_content=self.prompt_content,
            engineer_name=self.engineer_name
        )
        
        self.assertIsNotNone(version.id)
        self.assertEqual(version.version_number, 1)
        self.assertEqual(version.description, self.description)
        self.assertEqual(version.prompt_content, self.prompt_content)
        self.assertEqual(version.engineer_name, self.engineer_name)
        self.assertIsNotNone(version.created_at)

    def test_prompt_version_str(self):
        """Тест метода __str__ модели PromptVersion."""
        version = PromptVersion.objects.create(
            version_number=1,
            description=self.description,
            prompt_content=self.prompt_content,
            engineer_name=self.engineer_name
        )
        
        expected_str = f'Версия {version.version_number}: {self.description[:50]}'
        self.assertEqual(str(version), expected_str)

    def test_get_generated_content_count_empty(self):
        """Тест метода get_generated_content_count для версии без контента."""
        version = PromptVersion.objects.create(
            version_number=1,
            description=self.description,
            prompt_content=self.prompt_content,
            engineer_name=self.engineer_name
        )
        
        count = version.get_generated_content_count()
        self.assertEqual(count, 0)

    def test_get_generated_content_count_with_content(self):
        """Тест метода get_generated_content_count для версии с контентом."""
        version = PromptVersion.objects.create(
            version_number=1,
            description=self.description,
            prompt_content=self.prompt_content,
            engineer_name=self.engineer_name
        )
        
        # Создаем тестовый ContentType
        content_type = ContentType.objects.create(
            app_label='store',
            model='product'
        )
        
        # Создаем GeneratedContent
        GeneratedContent.objects.create(
            prompt_version=version,
            content_type=content_type,
            object_id=1,
            generated_data={'test': 'data'},
            status='SUCCESS'
        )
        
        count = version.get_generated_content_count()
        self.assertEqual(count, 1)

    def test_get_reviewed_content_count_empty(self):
        """Тест метода get_reviewed_content_count для версии без проверенного контента."""
        version = PromptVersion.objects.create(
            version_number=1,
            description=self.description,
            prompt_content=self.prompt_content,
            engineer_name=self.engineer_name
        )
        
        count = version.get_reviewed_content_count()
        self.assertEqual(count, 0)

    def test_get_reviewed_content_count_with_reviewed(self):
        """Тест метода get_reviewed_content_count для версии с проверенным контентом."""
        version = PromptVersion.objects.create(
            version_number=1,
            description=self.description,
            prompt_content=self.prompt_content,
            engineer_name=self.engineer_name
        )
        
        content_type = ContentType.objects.create(
            app_label='store',
            model='product'
        )
        
        # Создаем проверенный контент
        GeneratedContent.objects.create(
            prompt_version=version,
            content_type=content_type,
            object_id=1,
            generated_data={'test': 'data'},
            status='REVIEWED',
            reviewed_at=timezone.now()
        )
        
        # Создаем непроверенный контент
        GeneratedContent.objects.create(
            prompt_version=version,
            content_type=content_type,
            object_id=2,
            generated_data={'test': 'data2'},
            status='SUCCESS',
            reviewed_at=None
        )
        
        count = version.get_reviewed_content_count()
        self.assertEqual(count, 1)

    def test_get_average_rating_empty(self):
        """Тест метода get_average_rating для версии без оценок."""
        version = PromptVersion.objects.create(
            version_number=1,
            description=self.description,
            prompt_content=self.prompt_content,
            engineer_name=self.engineer_name
        )
        
        rating = version.get_average_rating()
        self.assertIsNone(rating)

    def test_get_average_rating_with_ratings(self):
        """Тест метода get_average_rating для версии с оценками."""
        version = PromptVersion.objects.create(
            version_number=1,
            description=self.description,
            prompt_content=self.prompt_content,
            engineer_name=self.engineer_name
        )
        
        content_type = ContentType.objects.create(
            app_label='store',
            model='product'
        )
        
        # Создаем контент с оценками
        GeneratedContent.objects.create(
            prompt_version=version,
            content_type=content_type,
            object_id=1,
            generated_data={'test': 'data'},
            status='REVIEWED',
            rating=4
        )
        
        GeneratedContent.objects.create(
            prompt_version=version,
            content_type=content_type,
            object_id=2,
            generated_data={'test': 'data2'},
            status='REVIEWED',
            rating=5
        )
        
        GeneratedContent.objects.create(
            prompt_version=version,
            content_type=content_type,
            object_id=3,
            generated_data={'test': 'data3'},
            status='REVIEWED',
            rating=3
        )
        
        rating = version.get_average_rating()
        self.assertIsNotNone(rating)
        self.assertEqual(rating, 4.0)  # (4 + 5 + 3) / 3 = 4.0

    def test_get_review_percentage_zero(self):
        """Тест метода get_review_percentage для версии без контента."""
        version = PromptVersion.objects.create(
            version_number=1,
            description=self.description,
            prompt_content=self.prompt_content,
            engineer_name=self.engineer_name
        )
        
        percentage = version.get_review_percentage()
        self.assertEqual(percentage, 0.0)

    def test_get_review_percentage_partial(self):
        """Тест метода get_review_percentage для версии с частично проверенным контентом."""
        version = PromptVersion.objects.create(
            version_number=1,
            description=self.description,
            prompt_content=self.prompt_content,
            engineer_name=self.engineer_name
        )
        
        content_type = ContentType.objects.create(
            app_label='store',
            model='product'
        )
        
        # Создаем 3 контента, из них 2 проверенных
        GeneratedContent.objects.create(
            prompt_version=version,
            content_type=content_type,
            object_id=1,
            generated_data={'test': 'data'},
            status='REVIEWED',
            reviewed_at=timezone.now()
        )
        
        GeneratedContent.objects.create(
            prompt_version=version,
            content_type=content_type,
            object_id=2,
            generated_data={'test': 'data2'},
            status='REVIEWED',
            reviewed_at=timezone.now()
        )
        
        GeneratedContent.objects.create(
            prompt_version=version,
            content_type=content_type,
            object_id=3,
            generated_data={'test': 'data3'},
            status='SUCCESS',
            reviewed_at=None
        )
        
        percentage = version.get_review_percentage()
        self.assertEqual(percentage, round((2 / 3) * 100, 2))

    def test_get_latest_version(self):
        """Тест класс-метода get_latest_version."""
        # Создаем несколько версий
        version1 = PromptVersion.objects.create(
            version_number=1,
            description='Версия 1',
            prompt_content='Контент 1',
            engineer_name=self.engineer_name
        )
        
        version2 = PromptVersion.objects.create(
            version_number=2,
            description='Версия 2',
            prompt_content='Контент 2',
            engineer_name=self.engineer_name
        )
        
        version3 = PromptVersion.objects.create(
            version_number=3,
            description='Версия 3',
            prompt_content='Контент 3',
            engineer_name=self.engineer_name
        )
        
        latest = PromptVersion.get_latest_version()
        self.assertEqual(latest.version_number, 3)
        self.assertEqual(latest.id, version3.id)

    def test_get_next_version_number_first(self):
        """Тест класс-метода get_next_version_number для первой версии."""
        next_number = PromptVersion.get_next_version_number()
        self.assertEqual(next_number, 1)

    def test_get_next_version_number_subsequent(self):
        """Тест класс-метода get_next_version_number для последующих версий."""
        PromptVersion.objects.create(
            version_number=1,
            description='Версия 1',
            prompt_content='Контент 1',
            engineer_name=self.engineer_name
        )
        
        PromptVersion.objects.create(
            version_number=2,
            description='Версия 2',
            prompt_content='Контент 2',
            engineer_name=self.engineer_name
        )
        
        next_number = PromptVersion.get_next_version_number()
        self.assertEqual(next_number, 3)

    def test_automatic_version_number_generation(self):
        """Тест автоматической генерации номера версии."""
        # Создаем версию без указания номера
        version1 = PromptVersion.objects.create(
            version_number=PromptVersion.get_next_version_number(),
            description='Версия 1',
            prompt_content='Контент 1',
            engineer_name=self.engineer_name
        )
        
        self.assertEqual(version1.version_number, 1)
        
        # Создаем следующую версию
        version2 = PromptVersion.objects.create(
            version_number=PromptVersion.get_next_version_number(),
            description='Версия 2',
            prompt_content='Контент 2',
            engineer_name=self.engineer_name
        )
        
        self.assertEqual(version2.version_number, 2)

    def test_ordering_by_version_number(self):
        """Тест сортировки по version_number (убывание)."""
        version1 = PromptVersion.objects.create(
            version_number=1,
            description='Версия 1',
            prompt_content='Контент 1',
            engineer_name=self.engineer_name
        )
        
        version2 = PromptVersion.objects.create(
            version_number=2,
            description='Версия 2',
            prompt_content='Контент 2',
            engineer_name=self.engineer_name
        )
        
        version3 = PromptVersion.objects.create(
            version_number=3,
            description='Версия 3',
            prompt_content='Контент 3',
            engineer_name=self.engineer_name
        )
        
        versions = list(PromptVersion.objects.all())
        self.assertEqual(versions[0].version_number, 3)
        self.assertEqual(versions[1].version_number, 2)
        self.assertEqual(versions[2].version_number, 1)


class GeneratedContentModelTest(TestCase):
    """Тесты для модели GeneratedContent."""

    def setUp(self):
        """Подготовка тестовых данных."""
        self.prompt_version = PromptVersion.objects.create(
            version_number=1,
            description='Тестовое описание',
            prompt_content='Тестовое содержимое',
            engineer_name='Иван Иванов'
        )
        
        self.content_type = ContentType.objects.create(
            app_label='store',
            model='product'
        )

    def test_create_generated_content(self):
        """Тест создания GeneratedContent."""
        generated_data = {'name': 'Test Product', 'description': 'Test Description'}
        
        content = GeneratedContent.objects.create(
            prompt_version=self.prompt_version,
            content_type=self.content_type,
            object_id=1,
            generated_data=generated_data,
            status='SUCCESS'
        )
        
        self.assertIsNotNone(content.id)
        self.assertEqual(content.prompt_version, self.prompt_version)
        self.assertEqual(content.content_type, self.content_type)
        self.assertEqual(content.object_id, 1)
        self.assertEqual(content.generated_data, generated_data)
        self.assertEqual(content.status, 'SUCCESS')
        self.assertIsNotNone(content.created_at)

    def test_generated_content_str(self):
        """Тест метода __str__ модели GeneratedContent."""
        content = GeneratedContent.objects.create(
            prompt_version=self.prompt_version,
            content_type=self.content_type,
            object_id=1,
            generated_data={'test': 'data'},
            status='SUCCESS'
        )
        
        expected_str = f'GeneratedContent #{content.id} (product, статус: Успешно сгенерирован)'
        self.assertEqual(str(content), expected_str)

    def test_generated_content_without_prompt_version(self):
        """Тест создания GeneratedContent без prompt_version."""
        content = GeneratedContent.objects.create(
            prompt_version=None,
            content_type=self.content_type,
            object_id=1,
            generated_data={'test': 'data'},
            status='PENDING'
        )
        
        self.assertIsNone(content.prompt_version)

    def test_generated_content_status_choices(self):
        """Тест различных статусов GeneratedContent."""
        statuses = ['PENDING', 'PROCESSING', 'SUCCESS', 'FAILURE', 'REVIEWED']
        
        for i, status in enumerate(statuses):
            content = GeneratedContent.objects.create(
                prompt_version=self.prompt_version,
                content_type=self.content_type,
                object_id=i + 1,
                generated_data={'test': 'data'},
                status=status
            )
            
            self.assertEqual(content.status, status)

    def test_generated_content_reviewed_at(self):
        """Тест поля reviewed_at."""
        reviewed_time = timezone.now()
        
        content = GeneratedContent.objects.create(
            prompt_version=self.prompt_version,
            content_type=self.content_type,
            object_id=1,
            generated_data={'test': 'data'},
            status='REVIEWED',
            reviewed_at=reviewed_time
        )
        
        self.assertEqual(content.reviewed_at, reviewed_time)

    def test_generated_content_rating(self):
        """Тест поля rating."""
        content = GeneratedContent.objects.create(
            prompt_version=self.prompt_version,
            content_type=self.content_type,
            object_id=1,
            generated_data={'test': 'data'},
            status='REVIEWED',
            rating=5
        )
        
        self.assertEqual(content.rating, 5)

    def test_generated_content_relationship_with_prompt_version(self):
        """Тест связи GeneratedContent с PromptVersion."""
        content = GeneratedContent.objects.create(
            prompt_version=self.prompt_version,
            content_type=self.content_type,
            object_id=1,
            generated_data={'test': 'data'},
            status='SUCCESS'
        )
        
        # Проверяем обратную связь
        related_content = self.prompt_version.generated_content.all()
        self.assertIn(content, related_content)
        self.assertEqual(related_content.count(), 1)

    def test_generated_content_ordering(self):
        """Тест сортировки GeneratedContent по created_at (убывание)."""
        content1 = GeneratedContent.objects.create(
            prompt_version=self.prompt_version,
            content_type=self.content_type,
            object_id=1,
            generated_data={'test': 'data1'},
            status='SUCCESS'
        )
        
        # Небольшая задержка для разницы во времени
        import time
        time.sleep(0.01)
        
        content2 = GeneratedContent.objects.create(
            prompt_version=self.prompt_version,
            content_type=self.content_type,
            object_id=2,
            generated_data={'test': 'data2'},
            status='SUCCESS'
        )
        
        contents = list(GeneratedContent.objects.all())
        self.assertEqual(contents[0].id, content2.id)
        self.assertEqual(contents[1].id, content1.id)

