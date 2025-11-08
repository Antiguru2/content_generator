"""
Тесты для представлений content_generator.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone

from content_generator.models import PromptVersion, GeneratedContent

User = get_user_model()


class BaseViewTest(TestCase):
    """Базовый класс для тестов представлений."""

    def setUp(self):
        """Подготовка тестовых данных."""
        self.client = Client()
        
        # Создаем пользователей с разными ролями
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            username='admin'
        )
        self.admin_user.is_staff = True
        self.admin_user.save()
        
        # Создаем группу admin
        admin_group, _ = Group.objects.get_or_create(name='admin')
        self.admin_user.groups.add(admin_group)
        
        self.engineer_user = User.objects.create_user(
            email='engineer@test.com',
            password='testpass123',
            username='engineer'
        )
        
        # Создаем группу engineer
        engineer_group, _ = Group.objects.get_or_create(name='engineer')
        self.engineer_user.groups.add(engineer_group)
        
        self.regular_user = User.objects.create_user(
            email='regular@test.com',
            password='testpass123',
            username='regular'
        )
        
        # Создаем тестовые версии промптов
        self.prompt_version1 = PromptVersion.objects.create(
            version_number=1,
            description='Версия 1',
            prompt_content='Содержимое версии 1',
            engineer_name='Иван Иванов'
        )
        
        self.prompt_version2 = PromptVersion.objects.create(
            version_number=2,
            description='Версия 2',
            prompt_content='Содержимое версии 2',
            engineer_name='Петр Петров'
        )
        
        # Создаем ContentType для тестов
        self.content_type = ContentType.objects.create(
            app_label='store',
            model='product'
        )


class PromptVersionListViewTest(BaseViewTest):
    """Тесты для PromptVersionListView."""

    def test_list_view_requires_login(self):
        """Тест, что список версий требует авторизации."""
        url = reverse('prompt_version_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Редирект на страницу входа

    def test_list_view_requires_admin_or_engineer(self):
        """Тест, что список версий требует роль admin или engineer."""
        self.client.login(email='regular@test.com', password='testpass123')
        url = reverse('prompt_version_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)  # Доступ запрещен

    def test_list_view_admin_access(self):
        """Тест доступа администратора к списку версий."""
        self.client.login(email='admin@test.com', password='testpass123')
        url = reverse('prompt_version_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('prompt_versions', response.context)

    def test_list_view_engineer_access(self):
        """Тест доступа инженера к списку версий."""
        self.client.login(email='engineer@test.com', password='testpass123')
        url = reverse('prompt_version_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_list_view_pagination(self):
        """Тест пагинации в списке версий."""
        # Создаем больше 10 версий для тестирования пагинации
        for i in range(15):
            PromptVersion.objects.create(
                version_number=i + 3,
                description=f'Версия {i + 3}',
                prompt_content=f'Содержимое версии {i + 3}',
                engineer_name='Тестовый инженер'
            )
        
        self.client.login(email='admin@test.com', password='testpass123')
        url = reverse('prompt_version_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_paginated'])

    def test_list_view_statistics(self):
        """Тест отображения статистики в списке версий."""
        # Создаем GeneratedContent для версии
        GeneratedContent.objects.create(
            prompt_version=self.prompt_version1,
            content_type=self.content_type,
            object_id=1,
            generated_data={'test': 'data'},
            status='SUCCESS'
        )
        
        self.client.login(email='admin@test.com', password='testpass123')
        url = reverse('prompt_version_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('versions_with_stats', response.context)


class PromptVersionDetailViewTest(BaseViewTest):
    """Тесты для PromptVersionDetailView."""

    def test_detail_view_requires_login(self):
        """Тест, что детальный просмотр требует авторизации."""
        url = reverse('prompt_version_detail', kwargs={'id': self.prompt_version1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_detail_view_requires_admin_or_engineer(self):
        """Тест, что детальный просмотр требует роль admin или engineer."""
        self.client.login(email='regular@test.com', password='testpass123')
        url = reverse('prompt_version_detail', kwargs={'id': self.prompt_version1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_detail_view_displays_version(self):
        """Тест отображения версии в детальном просмотре."""
        self.client.login(email='admin@test.com', password='testpass123')
        url = reverse('prompt_version_detail', kwargs={'id': self.prompt_version1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['version'], self.prompt_version1)

    def test_detail_view_statistics(self):
        """Тест отображения статистики в детальном просмотре."""
        # Создаем GeneratedContent
        GeneratedContent.objects.create(
            prompt_version=self.prompt_version1,
            content_type=self.content_type,
            object_id=1,
            generated_data={'test': 'data'},
            status='SUCCESS',
            reviewed_at=timezone.now()
        )
        
        self.client.login(email='admin@test.com', password='testpass123')
        url = reverse('prompt_version_detail', kwargs={'id': self.prompt_version1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('stats', response.context)
        self.assertEqual(response.context['stats']['generated_count'], 1)


class PromptVersionCreateViewTest(BaseViewTest):
    """Тесты для PromptVersionCreateView."""

    def test_create_view_requires_login(self):
        """Тест, что создание версии требует авторизации."""
        url = reverse('prompt_version_create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_create_view_requires_admin_or_engineer(self):
        """Тест, что создание версии требует роль admin или engineer."""
        self.client.login(email='regular@test.com', password='testpass123')
        url = reverse('prompt_version_create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_create_view_get(self):
        """Тест GET запроса для создания версии."""
        self.client.login(email='admin@test.com', password='testpass123')
        url = reverse('prompt_version_create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)

    def test_create_view_post_valid(self):
        """Тест POST запроса для создания версии с валидными данными."""
        self.client.login(email='admin@test.com', password='testpass123')
        url = reverse('prompt_version_create')
        
        # Получаем следующий номер версии
        next_version = PromptVersion.get_next_version_number()
        
        data = {
            'description': 'Новая версия',
            'prompt_content': 'Содержимое новой версии',
            'engineer_name': 'Тестовый инженер'
        }
        
        response = self.client.post(url, data)
        # После успешного создания должен быть редирект на детальный просмотр
        self.assertEqual(response.status_code, 302)
        
        # Проверяем, что версия создана
        created_version = PromptVersion.objects.get(version_number=next_version)
        self.assertEqual(created_version.description, 'Новая версия')

    def test_create_view_automatic_version_number(self):
        """Тест автоматической генерации номера версии при создании."""
        self.client.login(email='admin@test.com', password='testpass123')
        url = reverse('prompt_version_create')
        
        data = {
            'description': 'Новая версия',
            'prompt_content': 'Содержимое новой версии',
            'engineer_name': 'Тестовый инженер'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        
        # Проверяем, что номер версии был автоматически сгенерирован
        created_version = PromptVersion.objects.latest('created_at')
        self.assertIsNotNone(created_version.version_number)


class PromptVersionUpdateViewTest(BaseViewTest):
    """Тесты для PromptVersionUpdateView."""

    def test_update_view_requires_login(self):
        """Тест, что редактирование версии требует авторизации."""
        url = reverse('prompt_version_update', kwargs={'id': self.prompt_version1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_update_view_requires_admin_or_engineer(self):
        """Тест, что редактирование версии требует роль admin или engineer."""
        self.client.login(email='regular@test.com', password='testpass123')
        url = reverse('prompt_version_update', kwargs={'id': self.prompt_version1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_update_view_get(self):
        """Тест GET запроса для редактирования версии."""
        self.client.login(email='admin@test.com', password='testpass123')
        url = reverse('prompt_version_update', kwargs={'id': self.prompt_version1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('version', response.context)

    def test_update_view_smart_versioning_content_changed(self):
        """Тест умного версионирования при изменении содержимого промпта."""
        self.client.login(email='admin@test.com', password='testpass123')
        url = reverse('prompt_version_update', kwargs={'id': self.prompt_version1.id})
        
        original_version_number = self.prompt_version1.version_number
        original_content = self.prompt_version1.prompt_content
        
        data = {
            'description': 'Обновленное описание',
            'prompt_content': 'Измененное содержимое промпта',
            'engineer_name': 'Новый инженер'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        
        # Проверяем, что создана новая версия
        new_version = PromptVersion.objects.get(version_number=original_version_number + 1)
        self.assertEqual(new_version.prompt_content, 'Измененное содержимое промпта')
        
        # Проверяем, что старая версия не изменилась
        old_version = PromptVersion.objects.get(id=self.prompt_version1.id)
        self.assertEqual(old_version.prompt_content, original_content)

    def test_update_view_smart_versioning_description_only(self):
        """Тест умного версионирования при изменении только описания."""
        self.client.login(email='admin@test.com', password='testpass123')
        url = reverse('prompt_version_update', kwargs={'id': self.prompt_version1.id})
        
        original_version_number = self.prompt_version1.version_number
        original_content = self.prompt_version1.prompt_content
        
        data = {
            'description': 'Только обновленное описание',
            'prompt_content': original_content,  # Содержимое не изменилось
            'engineer_name': 'Новый инженер'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        
        # Проверяем, что новая версия НЕ создана
        versions_count = PromptVersion.objects.filter(version_number=original_version_number + 1).count()
        self.assertEqual(versions_count, 0)
        
        # Проверяем, что текущая версия обновлена
        updated_version = PromptVersion.objects.get(id=self.prompt_version1.id)
        self.assertEqual(updated_version.description, 'Только обновленное описание')
        self.assertEqual(updated_version.prompt_content, original_content)


class PromptVersionCloneViewTest(BaseViewTest):
    """Тесты для PromptVersionCloneView."""

    def test_clone_view_requires_login(self):
        """Тест, что клонирование версии требует авторизации."""
        url = reverse('prompt_version_clone', kwargs={'id': self.prompt_version1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_clone_view_requires_admin_or_engineer(self):
        """Тест, что клонирование версии требует роль admin или engineer."""
        self.client.login(email='regular@test.com', password='testpass123')
        url = reverse('prompt_version_clone', kwargs={'id': self.prompt_version1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_clone_view_creates_new_version(self):
        """Тест создания новой версии при клонировании."""
        self.client.login(email='admin@test.com', password='testpass123')
        url = reverse('prompt_version_clone', kwargs={'id': self.prompt_version1.id})
        
        original_count = PromptVersion.objects.count()
        next_version_number = PromptVersion.get_next_version_number()
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        
        # Проверяем, что создана новая версия
        self.assertEqual(PromptVersion.objects.count(), original_count + 1)
        
        cloned_version = PromptVersion.objects.get(version_number=next_version_number)
        self.assertEqual(cloned_version.prompt_content, self.prompt_version1.prompt_content)
        self.assertIn('Клон версии', cloned_version.description)

    def test_clone_view_description_format(self):
        """Тест формата описания клонированной версии."""
        self.client.login(email='admin@test.com', password='testpass123')
        url = reverse('prompt_version_clone', kwargs={'id': self.prompt_version1.id})
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        
        next_version_number = PromptVersion.get_next_version_number() - 1
        cloned_version = PromptVersion.objects.get(version_number=next_version_number)
        expected_description = f'Клон версии {self.prompt_version1.version_number}: {self.prompt_version1.description}'
        self.assertEqual(cloned_version.description, expected_description)


class PromptVersionDeleteViewTest(BaseViewTest):
    """Тесты для PromptVersionDeleteView."""

    def test_delete_view_requires_login(self):
        """Тест, что удаление версии требует авторизации."""
        url = reverse('prompt_version_delete', kwargs={'id': self.prompt_version1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_delete_view_requires_admin(self):
        """Тест, что удаление версии требует роль admin."""
        # Инженер не может удалять
        self.client.login(email='engineer@test.com', password='testpass123')
        url = reverse('prompt_version_delete', kwargs={'id': self.prompt_version1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        
        # Обычный пользователь не может удалять
        self.client.login(email='regular@test.com', password='testpass123')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_delete_view_admin_access(self):
        """Тест доступа администратора к удалению версии."""
        self.client.login(email='admin@test.com', password='testpass123')
        url = reverse('prompt_version_delete', kwargs={'id': self.prompt_version1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_delete_view_prevents_deletion_of_used_version(self):
        """Тест запрета удаления используемой версии."""
        # Создаем GeneratedContent для версии
        GeneratedContent.objects.create(
            prompt_version=self.prompt_version1,
            content_type=self.content_type,
            object_id=1,
            generated_data={'test': 'data'},
            status='SUCCESS'
        )
        
        self.client.login(email='admin@test.com', password='testpass123')
        url = reverse('prompt_version_delete', kwargs={'id': self.prompt_version1.id})
        response = self.client.get(url)
        
        # Должен быть редирект на детальный просмотр с сообщением об ошибке
        self.assertEqual(response.status_code, 302)

    def test_delete_view_allows_deletion_of_unused_version(self):
        """Тест разрешения удаления неиспользуемой версии."""
        self.client.login(email='admin@test.com', password='testpass123')
        url = reverse('prompt_version_delete', kwargs={'id': self.prompt_version1.id})
        
        version_id = self.prompt_version1.id
        response = self.client.post(url)
        
        # После успешного удаления должен быть редирект на список
        self.assertEqual(response.status_code, 302)
        
        # Проверяем, что версия удалена
        self.assertFalse(PromptVersion.objects.filter(id=version_id).exists())


class PromptVersionCompareViewTest(BaseViewTest):
    """Тесты для PromptVersionCompareView."""

    def test_compare_view_requires_login(self):
        """Тест, что сравнение версий требует авторизации."""
        url = reverse('prompt_version_compare', kwargs={
            'id1': self.prompt_version1.id,
            'id2': self.prompt_version2.id
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_compare_view_requires_admin_or_engineer(self):
        """Тест, что сравнение версий требует роль admin или engineer."""
        self.client.login(email='regular@test.com', password='testpass123')
        url = reverse('prompt_version_compare', kwargs={
            'id1': self.prompt_version1.id,
            'id2': self.prompt_version2.id
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_compare_view_displays_comparison(self):
        """Тест отображения сравнения версий."""
        self.client.login(email='admin@test.com', password='testpass123')
        url = reverse('prompt_version_compare', kwargs={
            'id1': self.prompt_version1.id,
            'id2': self.prompt_version2.id
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('version1', response.context)
        self.assertIn('version2', response.context)
        self.assertIn('comparison', response.context)
        self.assertIn('stats', response.context)

    def test_compare_view_display_mode(self):
        """Тест режима отображения сравнения."""
        self.client.login(email='admin@test.com', password='testpass123')
        url = reverse('prompt_version_compare', kwargs={
            'id1': self.prompt_version1.id,
            'id2': self.prompt_version2.id
        })
        
        # Тест режима side-by-side (по умолчанию)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['display_mode'], 'side-by-side')
        
        # Тест режима unified-diff
        response = self.client.get(url + '?mode=unified-diff')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['display_mode'], 'unified-diff')

