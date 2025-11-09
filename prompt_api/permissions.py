"""
Модуль для управления правами доступа к API подсистемы Prompts.
Реализует проверку ролей admin и engineer для REST API.
"""

from rest_framework import permissions
from content_generator.permissions import is_admin, is_engineer, is_admin_or_engineer


class AdminOrEngineerPermission(permissions.BasePermission):
    """
    Разрешение для операций просмотра, создания и редактирования.
    Требует авторизации и роли admin или engineer.
    """
    
    def has_permission(self, request, view):
        """
        Проверяет, имеет ли пользователь права доступа.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        return is_admin_or_engineer(request.user)


class AdminPermission(permissions.BasePermission):
    """
    Разрешение для операций удаления.
    Требует авторизации и роли admin.
    """
    
    def has_permission(self, request, view):
        """
        Проверяет, имеет ли пользователь права доступа.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        return is_admin(request.user)

