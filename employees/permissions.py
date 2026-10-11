from rest_framework import permissions

class IsAdminUserCustom(permissions.BasePermission):
    """Доступ только для Администратора"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser or request.user.groups.filter(name='Администратор').exists()
        )

class IsWatcherOrAdmin(permissions.BasePermission):
    """Доступ для Смотрителя и Администратора"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser or 
            request.user.groups.filter(name__in=['Смотритель', 'Администратор']).exists()
        )

class EmployeePermission(permissions.BasePermission):
    """
    Общие правила:
    - Просмотр (GET) доступен всем (даже Посетителям без авторизации/с ней).
    - Создание/Удаление/Полное изменение доступно только Администратору.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS: # GET, HEAD, OPTIONS
            return True
        return request.user.is_authenticated and (
            request.user.is_superuser or request.user.groups.filter(name='Администратор').exists()
        )
