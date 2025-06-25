# content_generator
Приложение для django для генерации контента

## Статус проекта

⚠️ **Внимание!** Данный проект находится в сыром состоянии:
- Код не протестирован
- Тесты отсутствуют
- Может содержать ошибки и недоработки
- Не рекомендуется для использования в продакшене

Используйте на свой страх и риск.

## Установка

### 1. Установить сабмодуль
```bash
git submodule add https://github.com/Antiguru2/content_generator.git content_generator
git submodule update --init --recursive
```

### 2. Добавить в settings.py
```python
INSTALLED_APPS = [
    # ... другие приложения ...
    
    # submodules
    'content_generator',
]
```

Так же добавьте в settings.py переменные из content_generator/local_settings.example.py

### 3. Добавить URL в основной urls.py
```python
urlpatterns += [
    path('content_generator/', include('content_generator.urls')),
    # ... другие URL ...
]
```

### 4. Добавить миксин к требуемой модели
В модели, к которой нужно добавить функциональность генерации контента, добавьте:

```python
from content_generator.mixins import ContentGeneratorMixin

class YourModel(models.Model, ContentGeneratorMixin):
    # ... ваши поля модели ...
    
    class Meta:
        # ... ваши настройки Meta ...
        pass
```

### 5. Настроить вывод поля content_generator в админке
В админке модели добавьте поле `content_generator` в `readonly_fields` и `fieldsets`:

```python
from django.contrib import admin

class YourModelAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {
            'fields': (
                # ... ваши поля ...
                'content_generator',
            )
        }),
    )
    readonly_fields = ('content_generator',)

admin.site.register(YourModel, YourModelAdmin)
```

### 6. Установить зависимости
Установите все необходимые зависимости из файлов req.txt:

```bash
find . -name 'req.txt' -exec pip install -r {} \;
```

После добавления миксина в админке Django появится дополнительное поле "Генератор контента (бета)" для объектов этой модели.

## Использование

1. После настройки в админке Django для моделей с миксином появится блок генерации контента
2. API endpoint доступен по адресу `/content_generator/generate/`
3. Для автоматической генерации контента используйте модель `PeriodContentGenerator`

### Технические детали

- **Frontend**: Скрипт для админки использует [Alpine.js](https://alpinejs.dev/) для интерактивности
- **API**: Взаимодействие с нейросетью происходит через REST API
- **Шаблоны**: Используется Django template system с кастомными шаблонами для админки

## Разработка

### Для сторонних разработчиков

Если вы хотите внести свой вклад в проект:

1. **Создайте новую ветку** для ваших изменений:
```bash
git checkout -b feature/your-feature-name
# или
git checkout -b fix/your-bug-fix
```

2. **Внесите изменения** и зафиксируйте их:
```bash
git add .
git commit -m "Описание ваших изменений"
```

3. **Отправьте ветку** в репозиторий:
```bash
git push origin feature/your-feature-name
```

4. **Создайте Pull Request** на GitHub с описанием изменений

### Рекомендации по именованию веток

- `feature/` - для новых функций
- `fix/` - для исправления багов
- `docs/` - для обновления документации
- `refactor/` - для рефакторинга кода

## Зависимости

- Django 3.2+
- requests (для API запросов)