from django.db import models
from django.contrib import admin
from django.contrib.auth import get_user_model


User = get_user_model()


class AbstractContentGenerator(models.Model):
    """
        Модель для добавления полей в классы требуещающих генерации контента
    """
    is_generated = models.BooleanField(
        default=False, editable=False,
        verbose_name='Сгенерировано?',
    )
    generated_as = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Кто сгенерил?',
    )

    class Meta:
        abstract = True

    @property
    @admin.display(description='Сгенерировано?')
    def get_is_generated(self):
        return self.is_generated
