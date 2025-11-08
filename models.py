import requests
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from django.db import models
from django.conf import settings
from django.apps import apps
from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Avg

User = get_user_model()


# ========== ПОДСИСТЕМА PROMPTS ==========

class PromptVersion(models.Model):
    """
    Модель версии промпта для генерации контента.
    Хранит версии промптов с возможностью отслеживания статистики использования.
    """
    version_number = models.IntegerField(
        unique=True,
        db_index=True,
        verbose_name='Номер версии',
        help_text='Уникальный номер версии промпта'
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
        indexes = [
            models.Index(fields=['version_number']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f'Версия {self.version_number}: {self.description[:50]}'

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
    def get_latest_version(cls):
        """
        Класс-метод для получения последней версии промпта.
        """
        return cls.objects.order_by('-version_number').first()

    @classmethod
    def get_next_version_number(cls):
        """
        Класс-метод для получения следующего номера версии.
        """
        latest = cls.objects.order_by('-version_number').first()
        if latest:
            return latest.version_number + 1
        return 1


# ========== ПОДСИСТЕМА GENERATION ==========

