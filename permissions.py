"""
Модуль для управления правами доступа к подсистеме Prompts.
Реализует проверку ролей admin и engineer для различных операций.
"""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied


def is_admin(user):
    """
    Проверяет, является ли пользователь администратором.
    
    Администратором считается:
    - Суперпользователь (is_superuser=True)
    - Пользователь с группой 'admin'
    - Пользователь с is_staff=True (опционально, если нет группы admin)
    
    Args:
        user: Объект пользователя Django
    
    Returns:
        bool: True, если пользователь является администратором
    """
    if not user or not user.is_authenticated:
        return False
    
    # Суперпользователь всегда является администратором
    if user.is_superuser:
        return True
    
    # Проверка группы 'admin'
    if user.groups.filter(name='admin').exists():
        return True
    
    # Если группа 'admin' не существует, используем is_staff как fallback
    # (для обратной совместимости)
    return user.is_staff


def is_engineer(user):
    """
    Проверяет, является ли пользователь инженером.
    
    Инженером считается:
    - Суперпользователь (is_superuser=True)
    - Пользователь с группой 'engineer'
    - Пользователь с группой 'Доступна генерация' (для обратной совместимости)
    
    Args:
        user: Объект пользователя Django
    
    Returns:
        bool: True, если пользователь является инженером
    """
    if not user or not user.is_authenticated:
        return False
    
    # Суперпользователь всегда является инженером
    if user.is_superuser:
        return True
    
    # Проверка группы 'engineer'
    if user.groups.filter(name='engineer').exists():
        return True
    
    # Проверка группы 'Доступна генерация' (для обратной совместимости)
    if user.groups.filter(name='Доступна генерация').exists():
        return True
    
    return False


def is_admin_or_engineer(user):
    """
    Проверяет, является ли пользователь администратором или инженером.
    
    Args:
        user: Объект пользователя Django
    
    Returns:
        bool: True, если пользователь является администратором или инженером
    """
    return is_admin(user) or is_engineer(user)


class AdminOrEngineerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Миксин для проверки прав доступа администратора или инженера.
    
    Используется для операций просмотра, создания и редактирования.
    Требует авторизации и роли admin или engineer.
    """
    
    def test_func(self):
        """
        Проверяет, является ли пользователь администратором или инженером.
        """
        return is_admin_or_engineer(self.request.user)
    
    def handle_no_permission(self):
        """
        Обрабатывает ситуацию, когда у пользователя нет прав доступа.
        """
        raise PermissionDenied("У вас нет прав доступа. Требуется роль администратора или инженера.")


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Миксин для проверки прав доступа администратора.
    
    Используется для операций удаления.
    Требует авторизации и роли admin.
    """
    
    def test_func(self):
        """
        Проверяет, является ли пользователь администратором.
        """
        return is_admin(self.request.user)
    
    def handle_no_permission(self):
        """
        Обрабатывает ситуацию, когда у пользователя нет прав доступа.
        """
        raise PermissionDenied("У вас нет прав доступа. Требуется роль администратора.")

