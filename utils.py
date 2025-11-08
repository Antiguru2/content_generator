import re 
import bs4 
import json
import requests

from django.db import models
from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from typing import (
    Union,
    Optional,
)
from bs4 import (
    BeautifulSoup,
    Tag,
)

from super_requester.models import SuperRequester
from main.models import SitePreferences
from super_requester.utils import send_message_about_error


super_requester = SuperRequester()

url_to_get_seo_params = getattr(settings, 'URL_TO_GET_SEO_PARAMS', None)
url_to_description_for_product = getattr(settings, 'URL_TO_DESCRIPTION_FOR_PRODUCT', None)
url_to_description_for_category = getattr(settings, 'URL_TO_DESCRIPTION_FOR_CATEGORY', None)
url_to_upgrade_name = getattr(settings, 'URL_TO_UPDATE_NAME', None)

url_to_set_some_params_for_product = getattr(settings, 'URL_TO_SET_TO_SOME_PARAMS_FOR_PRODUCT', None)
url_to_set_some_params_for_category = getattr(settings, 'URL_TO_SET_TO_SOME_PARAMS_FOR_CATEGORY', None)


def set_seo_params_of_model(model):
    """Генерирует SEO параметры для модели"""
    # print('set_seo_params_of_model')
    if not url_to_get_seo_params:
        print('Урл для получения сео параметров, НЕ УСТАНОВЛЕН')
        return
    
    description = model.description
    if not description:
        description = get_text_from_html(model.get_temporary_info_value())

    if len(description) > 317:
        description = description[:317]    

    data = {
        'name': model.name,
        'description': description
    }     
    # print('data', data)
    response = super_requester.get_response(
        url_to_get_seo_params, 
        method='POST',
        data=data
    )        

    try:
        response_data = json.loads(response.text)
        # print('response_data', response_data)
    except json.decoder.JSONDecodeError:
        send_message_about_error(
            'json.decoder.JSONDecodeError',
            'set_seo_params_of_model',
            error_data=f'Пришло {response.text}'
        )
        print('json.decoder.JSONDecodeError')
        return
    try:          
        seo_parameters = model.seo_parameters.super_object
        seo_parameters.title = response_data.get('title')
        seo_parameters.description = response_data.get('description')
        seo_parameters.save()         
    except:
        SEOParameters: models.Model = apps.get_model('seo_parameters', 'SEOParameters') 
        seo_parameters = SEOParameters.objects.create(
            content_type=ContentType.objects.get_for_model(model),
            object_id=model.id,
            title=response_data.get('title'),
            description=response_data.get('description'),
        )
               

def set_description_of_model(model, description=''): 
    """Генерирует описание для модели"""
    print('set_description_of_model')
    # print('model', model)
    description = model.get_temporary_info_value()
    if not description:
        print('temporary_info_value не получен')
        # return        

    name_model = model.__class__.__name__.lower()
    print('name_model', name_model)
    if name_model == 'category': 
        company_name = ''
        url_to_description = url_to_description_for_category

        if hasattr(model, 'site') and model.site and hasattr(model.site, 'preferences') and model.site.preferences and model.site.preferences.company_name:
            company_name = model.site.preferences.company_name
        else: 
            site_preferences = SitePreferences.get_model()
            company_name = getattr(site_preferences, 'company_name', '')

        data = {
            'company_profile': company_name,
            'category': model.name,
            'category_description': description,
        }        

    if name_model == 'product': 
        url_to_description = url_to_description_for_product
        data = {
            'category_name': model.category.name,
            'name': model.name,
            'description': description,
            'characteristics': model.all_attributs_data_as_str,
        }        
    print('data', data)
    if not url_to_description:
        print('Урл для получения description, НЕ УСТАНОВЛЕН')
        send_message_about_error(
            'Урл для получения description, НЕ УСТАНОВЛЕН',
            'main utils set_description_of_model',
            to_fix=True,
        )
        return
    
    response = super_requester.get_response(
        url_to_description, 
        method='POST',
        data=data
    )  
    print('statuse_code', response.status_code)
    if response and response.text:
        description = response.text
        print('description', description)
        try:
            data = json.loads(response.content)
            description = data.get('description_html', description)
        except json.decoder.JSONDecodeError:
            print('description')
            print('statuse_code', response.status_code)

            pass
        model.description = description
        model.save()       


def upgrade_name_of_model(model):
    """Улучшает название модели"""
    name_model = model.__class__.__name__.lower()
    if name_model == 'product':
        # print(' model.name',  model.name)
        # print('model.category.name', model.category.name)
        # print('model.all_attributs_data_as_str', model.all_attributs_data_as_str)
        data = {
            'name': model.name, 
            'category': model.category.name, 
            'attributes': model.all_attributs_data_as_str,
        }      
        response = super_requester.get_response(
            url_to_upgrade_name, 
            method='POST',
            data=data
        ) 
        
        new_name = response.text
        try:
            response_data = json.loads(response.text)
            # print('response_data', response_data)
            new_name = response_data.get('new_name')
        except json.decoder.JSONDecodeError:
            pass

        # print('new_name', new_name)
        model.name = new_name
        model.save()                        

def set_some_params_of_model(model, additional_prompt=None):
    """Комплексное улучшение параметров модели"""
    # print('set_some_params')
    company_name = ''
    if hasattr(model, 'site') and model.site and hasattr(model.site, 'preferences') and model.site.preferences:
        site_preferences = model.site.preferences
    else: 
        site_preferences = SitePreferences.get_model()

    name_model = model._meta.model_name
    if name_model == 'product':
        url_to_set_some_params = url_to_set_some_params_for_product
        category_name = ''
        if model.category and model.category.name:
            category_name = model.category.name

        data = {
            'company_name': getattr(site_preferences, 'company_name', ''),
            'company_profile': getattr(site_preferences, 'company_profile', ''),
            'product_name': model.name,
            'category_name': category_name,
            'product_attributes': model.all_attributs_data_as_str,
            'additional_prompt': additional_prompt,
        }   
    elif name_model == 'category':
        url_to_set_some_params = url_to_set_some_params_for_category
        data = {
            'category_name': model.name,
            'category_attributes': model.get_category_attributes_as_str(),
            'company_name': getattr(site_preferences, 'company_name', ''),
        }     

    if not url_to_set_some_params:
        print('Урл для получения set_some_params, НЕ УСТАНОВЛЕН')
        return
    
    response = super_requester.get_response(
        url_to_set_some_params, 
        method='POST',
        data=data
    )        

    try:
        response_data = json.loads(response.text)
        # print('response_data', response_data)
    except json.decoder.JSONDecodeError:
        send_message_about_error(
            'json.decoder.JSONDecodeError',
            'set_seo_params_of_model',
            error_data=f'Пришло {response.text}'
        )
        print('json.decoder.JSONDecodeError')
        return
    print('response_data', response_data)
    
    model.description = response_data.get('description', model.description)
    model.name = response_data.get('new_name', model.name)
    model.save()

    try:          
        seo_parameters = model.seo_parameters.super_object
        seo_parameters.title = response_data.get('title')
        seo_parameters.description = response_data.get('description')
        seo_parameters.save()         
    except:
        SEOParameters: models.Model = apps.get_model('seo_parameters', 'SEOParameters') 
        seo_parameters = SEOParameters.objects.create(
            content_type=ContentType.objects.get_for_model(model),
            object_id=model.id,
            title=response_data.get('title'),
            description=response_data.get('description'),
        )
            

def get_additional_header_elements():
    """Возвращает дополнительные элементы для заголовка"""
    result = None
    return result
        

def get_model_by_name(model_name: str) -> Optional[models.Model]:
    """Получает модель по имени"""
    try:
        return apps.get_model('store', model_name)
    except LookupError:
        return None