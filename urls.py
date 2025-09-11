from django.urls import path, include

from . import views
from . import api

urlpatterns = [
    # path('generate/', api.generate, name='generate'),

    # #API
    # path('webhook/', api.ContentGeneratorWebhookView.as_view(), name='webhook'),
]