from django.core.management.base import BaseCommand

from content_generator.models import PeriodContentGenerator


class Command(BaseCommand):
    help = 'Генерирует контент по заданному атрибуту (daily, weekly и т.д.)'

    def add_arguments(self, parser):
        parser.add_argument(
            'period',
            nargs='?',
            default='daily',
            help='Период генерации контента (например, daily, weekly)'
        )

    def handle(self, *args, **kwargs):
        period = kwargs['period']

        generate_content(period)
        



def generate_content(period):
    period_content_generators = PeriodContentGenerator.objects.filter(period=period)

    for period_content_generator in period_content_generators:
        period_content_generator.generate_content()