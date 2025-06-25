from django.urls import path

from . import views
from . import api

urlpatterns = [
    path('generate/', api.generate, name='generate'),
]