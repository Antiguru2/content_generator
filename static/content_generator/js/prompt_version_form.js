/**
 * JavaScript для формы PromptVersion
 * Реализует счетчик символов для поля prompt_content
 */

(function($) {
    'use strict';

    $(document).ready(function() {
        // Находим поле prompt_content
        var $promptContentField = $('#id_prompt_content');
        
        if ($promptContentField.length === 0) {
            return; // Поле не найдено, выходим
        }

        var maxLength = 50000;
        var currentLength = $promptContentField.val().length;
        
        // Создаем элемент счетчика
        var $counter = $('<div>', {
            'class': 'prompt-content-counter',
            'style': 'margin-top: 5px; font-size: 12px; color: #666;'
        });
        
        // Вставляем счетчик после поля
        $promptContentField.after($counter);
        
        // Функция обновления счетчика
        function updateCounter() {
            currentLength = $promptContentField.val().length;
            var remaining = maxLength - currentLength;
            var percentage = (currentLength / maxLength) * 100;
            
            // Определяем цвет в зависимости от заполненности
            var color = '#666';
            if (percentage >= 90) {
                color = '#d32f2f'; // Красный при >90%
            } else if (percentage >= 75) {
                color = '#f57c00'; // Оранжевый при >75%
            } else if (percentage >= 50) {
                color = '#fbc02d'; // Желтый при >50%
            }
            
            // Обновляем текст счетчика
            $counter.html(
                'Символов: <strong style="color: ' + color + ';">' + currentLength + '</strong> / ' + 
                maxLength + ' (осталось: <strong style="color: ' + color + ';">' + remaining + '</strong>)'
            );
            
            // Добавляем визуальную индикацию при приближении к лимиту
            if (percentage >= 90) {
                $counter.css('color', '#d32f2f');
                $counter.css('font-weight', 'bold');
            } else {
                $counter.css('color', '#666');
                $counter.css('font-weight', 'normal');
            }
        }
        
        // Обновляем счетчик при изменении содержимого
        $promptContentField.on('input keyup paste', function() {
            updateCounter();
        });
        
        // Инициализируем счетчик при загрузке страницы
        updateCounter();
        
        // Добавляем предупреждение при достижении лимита
        $promptContentField.on('input', function() {
            if (currentLength >= maxLength) {
                $counter.append(
                    $('<div>', {
                        'style': 'color: #d32f2f; font-weight: bold; margin-top: 5px;',
                        'text': '⚠ Достигнут максимальный лимит символов!'
                    })
                );
            }
        });
    });
})(django.jQuery);

