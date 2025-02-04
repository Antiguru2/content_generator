import requests

from django.db import models
from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType



class PeriodContentGenerator(models.Model):
    PERIODS_CHOICES = (
        ('daily', 'Ежедневно'),
        ('weekly', 'Еженедельно'),
    )
    django_model = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name='period_content_generators',
        verbose_name='Django модель',
    )
    site = models.ForeignKey(
        Site,
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

    class Meta:
        verbose_name = 'Генератор контента'
        verbose_name_plural = 'Генераторы контента'

    def __str__(self):
        result = self._meta.verbose_name
        return result
    
    def generate_content(self):
        some_model = self.django_model.model_class()

        data = {
            "topic": "Виды и строение промышленных газовых генераторов",
            "comment": "",
        }

        response = requests.post(
            f"{settings.AILENGO_BASE_URL}/basestore_article_creator",
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + settings.AILENGO_API_KEY,
            },
            json=data,
        )