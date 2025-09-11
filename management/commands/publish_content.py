from django.core.management.base import BaseCommand

from content_generator.models import ContentGenerator, ContentGeneratorLog


class Command(BaseCommand):
    help = 'Публикует запланированный контент'

    def handle(self, *args, **kwargs):
        ...
