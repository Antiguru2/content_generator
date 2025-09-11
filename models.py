import requests
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from django.db import models
from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class ContentGenerator(models.Model):
    PERIODS_CHOICES = (
        ('daily', 'Ежедневно'),
        ('weekly', 'Еженедельно'),
    )
    
    GENERATOR_TYPE_CHOICES = (
        ('articles', 'Статьи'),
    )

    site = models.ForeignKey(
        Site,
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name='period_content_generators',
        verbose_name=Site._meta.verbose_name,
    )
    period = models.CharField(
        choices=PERIODS_CHOICES, 
        max_length=50,
        default='daily',
        verbose_name='Период',
    )
    generator_type = models.CharField(
        max_length=50,
        choices=GENERATOR_TYPE_CHOICES,
        default='articles',
        verbose_name='Тип генератора',
    )
    is_enabled = models.BooleanField(
        default=True,
        verbose_name='Включён',
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Кто создал',
        help_text='Пользователь, создавший генератор',
    )
    last_run_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Последний запуск',
        help_text='Последний запуск work()',
    )

    class Meta:
        verbose_name = 'Генератор контента'
        verbose_name_plural = 'Генераторы контента'

    def __str__(self):
        result = self._meta.verbose_name
        if self.site:
            result += f": {self.site.domain}"
        return result
    

class ContentPlan():
    ...


class ContentGeneratorLog(models.Model):
    ...