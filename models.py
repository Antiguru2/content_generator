import requests
import threading

from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from django.db import models
from django.apps import apps
from django.conf import settings
from django.db.models import Avg
from django.utils import timezone
from django.contrib.sites.models import Site
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from ai_interface.models import AIAgent

User = get_user_model()


# ========== ПОДСИСТЕМА PROMPTS ==========

class Prompt(models.Model):
    """
    Тип промпта для генерации контента.
    Определяет назначение промпта (SEO, описание товара, статья и т.д.).
    """
    name = models.CharField(
        max_length=200,
        verbose_name='Название',
        help_text='Человекочитаемое название промпта'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание',
        help_text='Описание назначения промпта'
    )

    class Meta:
        verbose_name = 'Промпт'
        verbose_name_plural = 'Промпты'

    def __str__(self):
        return self.name

    def get_latest_version(self):
        """
        Возвращает последнюю версию промпта.
        """
        return self.versions.order_by('-version_number').first()

    def get_versions_count(self):
        """
        Возвращает количество версий промпта.
        """
        return self.versions.count()


class PromptVersion(models.Model):
    """
    Версия конкретного промпта для генерации контента.
    Хранит версии промптов с возможностью отслеживания статистики использования.
    """
    prompt = models.ForeignKey(
        'Prompt',
        on_delete=models.CASCADE,
        related_name='versions',
        verbose_name='Промпт',
        help_text='Тип промпта, к которому относится версия'
    )
    version_number = models.IntegerField(
        db_index=True,
        verbose_name='Номер версии',
        help_text='Номер версии в рамках конкретного промпта'
    )
    description = models.TextField(
        verbose_name='Описание версии',
        help_text='Описание изменений в данной версии промпта'
    )
    prompt_content = models.TextField(
        max_length=50000,
        verbose_name='Содержимое промпта',
        help_text='Текст промпта для генерации контента (максимум 50000 символов)'
    )
    engineer_name = models.CharField(
        max_length=100,
        verbose_name='Имя инженера',
        help_text='Имя инженера, создавшего данную версию'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Дата создания',
        help_text='Дата и время создания версии'
    )

    class Meta:
        db_table = 'prompt_versions'
        ordering = ['-version_number']
        verbose_name = 'Версия промпта'
        verbose_name_plural = 'Версии промптов'
        unique_together = [['prompt', 'version_number']]
        indexes = [
            models.Index(fields=['prompt', 'version_number']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        prompt_name = self.prompt.name if self.prompt else 'Unknown'
        return f'{prompt_name} - Версия {self.version_number}: {self.description[:50]}'

    def get_generated_content_count(self):
        """
        Возвращает количество сгенерированного контента для данной версии промпта.
        """
        try:
            GeneratedContent = apps.get_model('content_generator', 'GeneratedContent')
            if GeneratedContent:
                return GeneratedContent.objects.filter(prompt_version=self).count()
        except (LookupError, AttributeError):
            pass
        return 0

    def get_reviewed_content_count(self):
        """
        Возвращает количество проверенного контента для данной версии промпта.
        """
        try:
            GeneratedContent = apps.get_model('content_generator', 'GeneratedContent')
            if GeneratedContent:
                return GeneratedContent.objects.filter(
                    prompt_version=self,
                    reviewed_at__isnull=False
                ).count()
        except (LookupError, AttributeError):
            pass
        return 0

    def get_average_rating(self):
        """
        Возвращает средний рейтинг для сгенерированного контента данной версии промпта.
        Возвращает None, если нет оценок или система оценок не используется.
        """
        try:
            GeneratedContent = apps.get_model('content_generator', 'GeneratedContent')
            if GeneratedContent:
                result = GeneratedContent.objects.filter(
                    prompt_version=self,
                    rating__isnull=False
                ).aggregate(avg_rating=Avg('rating'))
                return result['avg_rating'] if result['avg_rating'] is not None else None
        except (LookupError, AttributeError):
            pass
        return None

    def get_review_percentage(self):
        """
        Возвращает процент проверенного контента от общего количества сгенерированного.
        """
        generated_count = self.get_generated_content_count()
        if generated_count == 0:
            return 0.0
        reviewed_count = self.get_reviewed_content_count()
        return round((reviewed_count / generated_count) * 100, 2)

    @classmethod
    def get_latest_version(cls, prompt=None):
        """
        Класс-метод для получения последней версии промпта.
        
        Args:
            prompt: Экземпляр Prompt или None. Если None, возвращает последнюю версию любого промпта.
        """
        queryset = cls.objects.all()
        if prompt:
            queryset = queryset.filter(prompt=prompt)
        return queryset.order_by('-version_number').first()

    def get_next_version_number(self):
        """
        Возвращает следующий номер версии для данного промпта.
        """
        latest = self.prompt.versions.order_by('-version_number').first()
        if latest:
            return latest.version_number + 1
        return 1

    @classmethod
    def get_next_version_number_for_prompt(cls, prompt):
        """
        Класс-метод для получения следующего номера версии для конкретного промпта.
        
        Args:
            prompt: Экземпляр Prompt
        """
        latest = prompt.versions.order_by('-version_number').first()
        if latest:
            return latest.version_number + 1
        return 1


# ========== ПОДСИСТЕМА GENERATION ==========

class Action(models.Model):
    """
    Действие для генерации контента.
    
    Хранит метаданные о действиях, которые можно выполнять для генерации контента.
    Используется для настройки доступных действий в UI и привязки к генераторам контента.
    """
    name = models.CharField(
        max_length=255,
        verbose_name='Название',
    )
    label = models.CharField(
        max_length=255,
        verbose_name='Заголовок',
    )
    icon = models.CharField(
        max_length=255,
        verbose_name='Иконка',
    )
    system_prompt = models.ForeignKey(
        Prompt,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='content_generators',
        verbose_name='Системный промпт',
    )
    prompt = models.ForeignKey(
        Prompt,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='generators',
        verbose_name='Промпт',
    )      

    class Meta:
        verbose_name = 'Действие'
        verbose_name_plural = 'Действия'

    def __str__(self):
        return f'{self.label} ({self.name})'


class ContentGenerator(models.Model):
    """
    Генератор контента для конкретной модели Django.
    
    Настраивает параметры генерации контента для определенного типа модели (Product, Category и т.д.).
    Позволяет связать модель с промптами, действиями и AI-провайдером для гибкой настройки
    генерации контента через админку Django без изменения кода.
    
    Ограничение: для каждой модели может быть только один генератор контента.
    """
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        unique=True,
        verbose_name='Модель',
    ) 
    actions = models.ManyToManyField(
        Action,
        verbose_name='Действия',
    )
    agent = models.ForeignKey(
        AIAgent,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='AI агент',
    )
    
    class Meta:
        verbose_name = 'Генератор контента'
        verbose_name_plural = 'Генераторы контента'
        indexes = [
            models.Index(fields=['content_type']),
        ]

    def __str__(self):
        model_name = self.content_type.model if self.content_type else 'Unknown'
        return f'Генератор для {model_name}'


class GeneratedContent(models.Model):
    """
    Модель сгенерированного контента.
    Хранит результаты генерации контента с привязкой к версиям промптов и задачам AI.
    """
    STATUS_CHOICES = (
        ('PENDING', 'Ожидает генерации'),
        ('PROCESSING', 'В процессе генерации'),
        ('SUCCESS', 'Успешно сгенерирован'),
        ('FAILURE', 'Ошибка генерации'),
        ('REVIEWED', 'Проверен'),
    )
    
    prompt_version = models.ForeignKey(
        'PromptVersion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_content',
        verbose_name='Версия промпта',
        help_text='Версия промпта, использованная для генерации'
    )
    ai_task = models.ForeignKey(
        'ai_interface.AITask',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='AI задача',
        help_text='Задача из ai_interface, связанная с генерацией'
    )
    # ИЗМЕНЕНИТЬ НА SUPER_OBJECT
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name='Тип контента',
        help_text='Тип связанного объекта (Product, Category и т.д.)'
    )
    object_id = models.PositiveIntegerField(
        verbose_name='ID объекта',
        help_text='ID связанного объекта'
    )
    content_object = GenericForeignKey('content_type', 'object_id')
    generated_data = models.JSONField(
        verbose_name='Сгенерированные данные',
        help_text='Данные, сгенерированные AI'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name='Статус генерации',
        help_text='Текущий статус процесса генерации'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Дата создания',
        help_text='Дата и время создания записи'
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата проверки',
        help_text='Дата и время проверки сгенерированного контента'
    )
    rating = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Рейтинг',
        help_text='Оценка качества сгенерированного контента (для будущей системы оценок)'
    )

    class Meta:
        db_table = 'generated_content'
        ordering = ['-created_at']
        verbose_name = 'Сгенерированный контент'
        verbose_name_plural = 'Сгенерированный контент'
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        content_type_name = self.content_type.model if self.content_type else 'Unknown'
        return f'GeneratedContent #{self.id} ({content_type_name}, статус: {self.get_status_display()})'

