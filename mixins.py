import re

from bs4 import BeautifulSoup

from django.utils.safestring import mark_safe
from django.contrib.admin.decorators import display

from super_requester.utils import send_message_about_error
from super_requester.models import SuperRequester
from content_generator.utils import (
    set_seo_params_of_model,
    set_description_of_model,
    upgrade_name_of_model,
    set_some_params_of_model,
)

super_requester = SuperRequester(
    count=10, 
    max_delay=5,
    proxy_mode='models'
)


class TextGeneratorMixin():
    '''
       Миксин позволяющий генерировать текст 
    '''
    def set_seo_params(self):
        set_seo_params_of_model(self)      

    def set_description(self):
        set_description_of_model(self)      

    def upgrade_name(self):
        upgrade_name_of_model(self)   

    def set_some_params(self, set_some_params=None):
        set_some_params_of_model(self, set_some_params)   


super_requester_for_image_generator = SuperRequester(
    count=1000, 
    max_delay=1,
    proxy_mode='models',
    incognito=True,
)

class ImageGeneratorMixin():
    '''
       Миксин позволяющий генерировать картинки 
    '''
    def get_images_by_text(self, text, img_count=20):
        syses = True
        images_data = []
        changed_text = re.sub(' ', '%20', text)
        response_text = ''

        print('while')
        while syses:
            # url = f'https://yandex.ru/images/search?isize=large&itype=png&lr=54&text={changed_text}&type=clipart'
            url = f'https://ya.ru/images/search?from=tabbar&text={changed_text}&isize=large&type=clipart'
            response = super_requester_for_image_generator.get_response(url)
            # print('response.text', response.text)
            if 'captcha-backgrounds' in response.text:
                print('------------------>>>>>>>>>   captcha-backgrounds')
            # else:
            syses = False
            
        send_message_about_error(
            error_text="response_text",
            name_sender=f"get_images_by_text",
            error_data='...',
            error_data_is_traceback=response.text,
        )
        bs_container = BeautifulSoup(response.text, 'lxml')

        images_containers = bs_container.select('div.SerpPage')
        print('images_containers', images_containers)

        for image_container in images_containers[:img_count]:
            good_image_link = image_container['href']
            good_caption = '-'
            good_url = '-'
            try:
                good_caption = image_container.find(class_='serp-item__snippet-description')['href']            
                good_url = image_container.find(class_='serp-item__snippet-title').text
            except:
                pass

            images_data.append({
                'good_image_link': f'https:{good_image_link}',
                'good_url': good_caption,
                'good_caption': good_url,

                }
            )
        print('images_data', images_data)
        return images_data, response_text

    # @property
    # @display(description='Кнопка')
    # def get_button_for_admin(self):
    #     return mark_safe(f"<a id='anchor_pictures' href='/change_img/?good_id={self.id}'><input type='button' value='Выбрать картинку из яндекс картинок'></a>")          


class HTMLGeneratorMixin():
    """
    Миксин для генерации html
    """
    def update_html_constructor(self, user_prompt):
        
        pass




class ContentGeneratorMixin(
    TextGeneratorMixin,
    ImageGeneratorMixin,
    HTMLGeneratorMixin,
):
    '''
       Миксин позволяющий генерировать контент 
    '''
    @property
    @display(description='Кнопка')
    def get_buttons_for_admin(self):
        # TODO: Нужно сделать инпут и отправку через alpine.js
        buttons_for_admin = str(
            f"<a id='set_seo_params_button' href='/set_seo_params/?class_name={self.__class__.__name__.lower()}&model_id={self.id}'><input type='button' value='Сгенерировать сео параметры'></a>"
            f" "
            f"<a id='set_description_button' href='/set_description/?class_name={self.__class__.__name__.lower()}&model_id={self.id}'><input type='button' value='Сгенерировать полное описание'></a>"
            f" "
            f"<a id='upgrade_name' href='/upgrade_name/?class_name={self.__class__.__name__.lower()}&model_id={self.id}'><input type='button' value='Улучшить название'></a>"  
            f" "
            f"<a id='anchor_pictures' href='/change_img/?product_id={self.id}'><input type='button' value='Выбрать картинку из яндекс картинок'></a>"               
            f" "
            f"<a id='anchor_pictures' href='/set_some_params/?class_name={self.__class__.__name__.lower()}&model_id={self.id}'><input type='button' value='Улучшить SEO параметры и description'></a>" 
        )
        # if self._meta.model_name == 'category':
        #     buttons_for_admin += str(
        #     )

        return mark_safe(buttons_for_admin)
    
    @property
    @display(description='Вы можете ввести описание своими словами')
    def сontent_generator_block(self):
        return mark_safe(
            "<script src='//unpkg.com/alpinejs' defer></script>"
            "<div x-data='сontentGeneratorBlock'>"
                "<div>"
                    "<textarea x-model='aditonalPrompt' x-show='textareaShow' rows='10' cols='40' style='width: 610px;' id='сontentGeneratorBlockTextarea'></textarea>"
                "</div>"
                f"<a @click.prevent='clickButton(event)' id='set_seo_params_button' href='/set_seo_params/?class_name={self.__class__.__name__.lower()}&model_id={self.id}'><input class='сontent_generator_button' type='button' value='Сгенерировать сео параметры'></a>"
                f" "
                f"<a @click.prevent='clickButton(event)' id='set_description_button' href='/set_description/?class_name={self.__class__.__name__.lower()}&model_id={self.id}'><input class='сontent_generator_button' type='button' value='Сгенерировать полное описание'></a>"
                f" "
                f"<a @click.prevent='clickButton(event)' id='upgrade_name' href='/upgrade_name/?class_name={self.__class__.__name__.lower()}&model_id={self.id}'><input class='сontent_generator_button' type='button' value='Улучшить название'></a>"
                f" "
                f"<a @click.prevent='clickButton($event)' id='anchor_pictures' href='/change_img/?product_id={self.id}'><input class='сontent_generator_button' type='button' value='Выбрать картинку из яндекс картинок'></a>"
                f" "
                f"<a @click.prevent='clickButton($event)' id='anchor_pictures' href='/set_some_params/?class_name={self.__class__.__name__.lower()}&model_id={self.id}'><input type='button' value='Улучшить SEO параметры и description'></a>" 
            "</div>"
            "<script>"
                "document.addEventListener('alpine:init', () => {"
                    "Alpine.data('сontentGeneratorBlock', () => ({"
                        "textareaShow: true,"
                        "aditonalPrompt: '',"
                        "init() {"
                            "console.log('init');"
                        "},"
                        "async clickButton(event) {"
                            "console.log('clickButton');"
                            "var aTag = event.target.parentNode;"
                            "console.log('aTag', aTag);"
                            "var url = `${aTag.getAttribute('href')}&additional_prompt=${this.aditonalPrompt}&`;"
                            "const response = await fetch(url);"
                            "console.log('url', url);"
                            "console.log('response', response);"
                        "},"
                "}))"
            "})"
            "</script>"
        )

    @property
    @display(description='Генерация контента (AI)')
    def content_generator_widget_iframe(self):
        """Возвращает айфрейм с виджетом генерации контента или сообщение о необходимости настройки.

        Ищет ContentGenerator для текущей модели по content_type.
        Если генератор найден - формирует URL с generator_id.
        Если генератор не найден - возвращает HTML с сообщением и ссылкой на создание.
        """
        from django.contrib.contenttypes.models import ContentType
        from django.urls import reverse
        from content_generator.models import ContentGenerator
        from django.core.exceptions import ObjectDoesNotExist
        
        # Получаем ContentType для текущей модели
        content_type = ContentType.objects.get_for_model(self)
        
        # Ищем ContentGenerator по content_type (теперь гарантирована уникальность)
        try:
            generator = ContentGenerator.objects.get(content_type=content_type)
        except ObjectDoesNotExist:
            generator = None
        
        if generator:
            # Если генератор найден - формируем URL с generator_id
            iframe_src = f"/content_generator_widget/?generator_id={generator.id}&obj_id={self.id}"
            iframe_html = (
                "<div id='cg-widget-container' style='width: 100%; max-width: none;'>"
                f"<iframe id='cg-widget-iframe' src='{iframe_src}' "
                "style=\"display:block; width: 100%; height: 80vh; min-height: 560px; "
                "border: 0; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,.08); background: #fff;\" "
                "loading='lazy' referrerpolicy='same-origin' allow='clipboard-read; clipboard-write' allowfullscreen></iframe>"
                "</div>"
                "<script>(function(){"
                "try {"
                "  var c = document.getElementById('cg-widget-container');"
                "  if(!c) return;"
                "  var flex = c.closest('.flex-container');"
                "  if (flex) {"
                "    var readonly = flex.querySelector('div.readonly');"
                "    if (readonly) {"
                "      readonly.style.flex = '1 1 100%';"
                "      readonly.style.width = '100%';"
                "      readonly.style.maxWidth = '100%';"
                "      readonly.style.paddingRight = '0';"
                "    }"
                "  }"
                "  var iframe = document.getElementById('cg-widget-iframe');"
                "  function fitHeight(){"
                "    if(!iframe) return;"
                "    var r = iframe.getBoundingClientRect();"
                "    var space = window.innerHeight - r.top - 24;"
                "    var h = Math.max(560, space);"
                "    iframe.style.height = h + 'px';"
                "  }"
                "  fitHeight();"
                "  window.addEventListener('resize', fitHeight);"
                "} catch(e) { /* no-op */ }"
                "})();</script>"
            )
            return mark_safe(iframe_html)
        else:
            # Если генератор не найден - возвращаем HTML с сообщением и ссылкой на создание
            create_url = reverse('admin:content_generator_contentgenerator_add')
            create_url_with_params = f"{create_url}?content_type={content_type.id}"
            
            message_html = (
                "<div style='padding: 20px; background: #fff3cd; border: 1px solid #ffc107; "
                "border-radius: 8px; margin: 20px 0;'>"
                "<h3 style='margin-top: 0; color: #856404;'>⚠️ Генератор контента не настроен</h3>"
                "<p style='color: #856404; margin-bottom: 15px;'>"
                f"Для модели <strong>{content_type.model}</strong> необходимо настроить генератор контента. "
                "Нажмите на кнопку ниже, чтобы создать генератор с предустановленным типом модели."
                "</p>"
                f"<a href='{create_url_with_params}' "
                "style='display: inline-block; padding: 10px 20px; background: #007bff; color: white; "
                "text-decoration: none; border-radius: 4px; font-weight: bold;'>"
                "Создать генератор контента"
                "</a>"
                "</div>"
            )
            return mark_safe(message_html)
    
    @property
    @display(description='Вы можете ввести описание своими словами')
    def get_set_some_params_link(self):
        if self._meta.model_name in ['category', 'product']:
            return mark_safe(
                f"<a id='anchor_pictures' href='/set_some_params/?class_name={self.__class__.__name__.lower()}&model_id={self.id}'>" 
                "<button style='float: right;'>Обновить</button>"
                "</a>"
            )