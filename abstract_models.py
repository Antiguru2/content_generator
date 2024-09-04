from django.db import models
from django.contrib import admin


class AbstractContentGenerator(models.Model):
    """
        Модель для добавления полей в классы требуещающих генерации контента
    """
    is_generated = models.BooleanField(
        default=False, editable=False,
        verbose_name='Сгенерировано?',
    )

    class Meta:
        abstract = True

    @property
    @admin.display(description='Сгенерировано?')
    def get_is_generated(self):
        return self.is_generated
