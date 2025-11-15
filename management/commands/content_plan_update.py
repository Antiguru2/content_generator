import time
from typing import Optional, Dict, Any

from django.core.management.base import BaseCommand, CommandError
from django.contrib.sites.models import Site
from django.conf import settings
from django.utils import timezone

from content_generator.models import ContentPlan, Topic, ContentGeneratorLog
from ai_interface.models import AIAgent, AITask


class Command(BaseCommand):
    help = 'Обновляет контент-план'

    def handle(self, *args, **options):
        ...