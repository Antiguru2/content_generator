import requests
from typing import List, Dict, Any
from django.conf import settings
from django.contrib.sites.models import Site

from content_generator.models import ContentPlan, ContentGeneratorLog
