import requests

from django.apps import apps
from django.conf import settings
from django.http import JsonResponse

def generate(request):
    natural_key = request.GET.get('natural_key')
    model_id = request.GET.get('model_id')
    additional_prompt = request.GET.get('additional_prompt')
    print(natural_key, model_id, additional_prompt)
    some_model = apps.get_model(natural_key)
    some_obj = some_model.objects.get(id=model_id)
    url = settings.CONTENT_GENERATOR__WEBHOOK_URL
    data = {
        "mark_name": some_obj.auto_mark.name, 
        "service_name": some_obj.service.name,
        "additional_prompt": additional_prompt,
    }
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {settings.CONTENT_GENERATOR__API_KEY}',
    }
    response = requests.post(url, json=data, headers=headers)
    print(response.json())
    return JsonResponse({
        'status': 'ok',
        'data': response.json(),
    })