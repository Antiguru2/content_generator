from rest_framework import serializers
from .models import PromptVersion


# ========== ПОДСИСТЕМА PROMPTS ==========

class PromptVersionSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для версий промптов.
    Используется для списка и базовых операций.
    """
    class Meta:
        model = PromptVersion
        fields = [
            'id',
            'version_number',
            'description',
            'prompt_content',
            'engineer_name',
            'created_at',
        ]
        read_only_fields = ['id', 'version_number', 'created_at']


class PromptVersionDetailSerializer(serializers.ModelSerializer):
    """
    Детальный сериализатор для версий промптов с включением статистики.
    Используется для детального просмотра версии.
    """
    generated_content_count = serializers.SerializerMethodField()
    reviewed_content_count = serializers.SerializerMethodField()
    review_percentage = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    
    class Meta:
        model = PromptVersion
        fields = [
            'id',
            'version_number',
            'description',
            'prompt_content',
            'engineer_name',
            'created_at',
            'generated_content_count',
            'reviewed_content_count',
            'review_percentage',
            'average_rating',
        ]
        read_only_fields = [
            'id',
            'version_number',
            'created_at',
            'generated_content_count',
            'reviewed_content_count',
            'review_percentage',
            'average_rating',
        ]
    
    def get_generated_content_count(self, obj):
        """Возвращает количество сгенерированного контента."""
        return obj.get_generated_content_count()
    
    def get_reviewed_content_count(self, obj):
        """Возвращает количество проверенного контента."""
        return obj.get_reviewed_content_count()
    
    def get_review_percentage(self, obj):
        """Возвращает процент проверенного контента."""
        return obj.get_review_percentage()
    
    def get_average_rating(self, obj):
        """Возвращает средний рейтинг."""
        return obj.get_average_rating()


class PromptVersionCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания новых версий промптов.
    Автоматически генерирует номер версии и заполняет engineer_name из запроса.
    """
    class Meta:
        model = PromptVersion
        fields = [
            'description',
            'prompt_content',
            'engineer_name',
        ]
    
    def create(self, validated_data):
        """
        Создает новую версию промпта с автоматической генерацией номера версии.
        """
        # Генерируем следующий номер версии
        version_number = PromptVersion.get_next_version_number()
        
        # Создаем новую версию
        version = PromptVersion.objects.create(
            version_number=version_number,
            **validated_data
        )
        
        return version


class PromptVersionUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обновления версий промптов.
    Реализует логику "умного версионирования":
    - При изменении prompt_content → создание новой версии
    - При изменении только description → обновление текущей версии
    """
    class Meta:
        model = PromptVersion
        fields = [
            'description',
            'prompt_content',
            'engineer_name',
        ]
    
    def update(self, instance, validated_data):
        """
        Обновляет версию промпта с реализацией "умного версионирования".
        """
        original_prompt_content = instance.prompt_content
        new_prompt_content = validated_data.get('prompt_content', original_prompt_content)
        new_description = validated_data.get('description', instance.description)
        new_engineer_name = validated_data.get('engineer_name', instance.engineer_name)
        
        # Проверяем, изменилось ли содержимое промпта
        if original_prompt_content != new_prompt_content:
            # Создаем новую версию при изменении содержимого
            new_version_number = PromptVersion.get_next_version_number()
            new_version = PromptVersion.objects.create(
                version_number=new_version_number,
                description=new_description,
                prompt_content=new_prompt_content,
                engineer_name=new_engineer_name,
            )
            return new_version
        else:
            # Обновляем только описание текущей версии
            instance.description = new_description
            instance.engineer_name = new_engineer_name
            instance.save()
            return instance
