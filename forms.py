from django import forms
from django.contrib.auth import get_user_model

from .models import Prompt, PromptVersion

User = get_user_model()


# ========== ПОДСИСТЕМА PROMPTS ==========

class PromptVersionForm(forms.ModelForm):
    """
    Форма для создания и редактирования версий промптов.
    Включает валидацию полей и автоматическое заполнение engineer_name.
    """
    class Meta:
        model = PromptVersion
        fields = ['prompt', 'description', 'prompt_content', 'engineer_name']
        widgets = {
            'prompt': forms.Select(attrs={
                'class': 'admin-form-select',
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'class': 'admin-form-textarea',
                'placeholder': 'Опишите изменения в данной версии промпта'
            }),
            'prompt_content': forms.Textarea(attrs={
                'rows': 20,
                'class': 'admin-form-textarea',
                'id': 'id_prompt_content',
                'maxlength': '50000',
                'placeholder': 'Введите содержимое промпта для генерации контента'
            }),
            'engineer_name': forms.TextInput(attrs={
                'class': 'admin-form-input',
                'readonly': True,
                'style': 'background-color: #f5f5f5;'
            }),
        }
        labels = {
            'prompt': 'Тип промпта',
            'description': 'Описание версии',
            'prompt_content': 'Содержимое промпта',
            'engineer_name': 'Автор',
        }
        help_texts = {
            'prompt': 'Выберите тип промпта, к которому относится данная версия.',
            'description': 'Обязательное поле. Опишите изменения в данной версии промпта.',
            'prompt_content': 'Текст промпта для генерации контента (максимум 50000 символов).',
            'engineer_name': 'Имя инженера, создавшего данную версию (заполняется автоматически).',
        }

    def __init__(self, *args, **kwargs):
        """
        Инициализация формы с автоматическим заполнением engineer_name из текущего пользователя.
        """
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Автоматическое заполнение engineer_name из текущего пользователя
        if self.user and self.user.is_authenticated:
            # Получаем полное имя пользователя или username
            if hasattr(self.user, 'get_full_name') and self.user.get_full_name():
                engineer_name = self.user.get_full_name()
            else:
                engineer_name = self.user.username
            self.fields['engineer_name'].initial = engineer_name
        
        # Делаем description обязательным полем
        self.fields['description'].required = True
        self.fields['prompt'].required = True
        
        # Фильтруем промпты только активными
        self.fields['prompt'].queryset = Prompt.objects.filter(is_active=True)

    def clean_prompt_content(self):
        """
        Валидация содержимого промпта: проверка максимальной длины.
        """
        prompt_content = self.cleaned_data.get('prompt_content', '')
        if len(prompt_content) > 50000:
            raise forms.ValidationError(
                f'Содержимое промпта не может превышать 50000 символов. '
                f'Текущая длина: {len(prompt_content)} символов.'
            )
        return prompt_content

    def clean_description(self):
        """
        Валидация описания: проверка на пустое значение.
        """
        description = self.cleaned_data.get('description', '').strip()
        if not description:
            raise forms.ValidationError('Описание версии является обязательным полем.')
        return description

