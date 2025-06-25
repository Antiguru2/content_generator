from django.contrib import admin
from django.template.loader import render_to_string


class ContentGeneratorMixin:

    def get_content_generator_block(self):
        self.natural_key = f"{self._meta.app_label}.{self.__class__.__name__.lower()}"
        return render_to_string('custom_admin/content_generator_admin.html', {
            'self': self,
        })
    
    @property
    @admin.display(description='Генератор контента (бета)')
    def content_generator(self):
        return self.get_content_generator_block()