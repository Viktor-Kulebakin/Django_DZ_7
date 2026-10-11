from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.utils import timezone
from .models import EmployeeProfile, EmployeeImage
from rest_framework import viewsets, status
from rest_framework.response import Response
from .serializers import EmployeeProfileSerializer
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action

from .models import EmployeeProfile
from .serializers import EmployeeProfileSerializer
from .permissions import EmployeePermission, IsWatcherOrAdmin


def index_view(request):
    """Главная страница: описание проекта и карточки сотрудников."""
    # Оптимально подтягиваем профили и связанные картинки
    employees_queryset = EmployeeProfile.objects.prefetch_related(
        Prefetch('images', queryset=EmployeeImage.objects.order_by('position', 'id'))
    )
    
    # 1. Общее количество сотрудников в базе данных
    total_employees = employees_queryset.count()
    
    # 2. Только 4 последних по дате приёма на работу
    latest_employees = employees_queryset.order_by('-date_joined')[:4]
    
    # 3. Вычисляем стаж в днях для каждого из 4-х сотрудников
    today = timezone.now().date()
    for emp in latest_employees:
        emp.experience_days = (today - emp.date_joined).days

    context = {
        'title': 'Главная страница', 
        'employees': latest_employees,  # Передаем только 4 последних
        'total_employees': total_employees  # Передаем общее количество
    }
    return render(request, 'employees/index.html', context)


def employee_list_view(request):
    """Список всех сотрудников с пагинацией."""
    # Подгружаем сотрудников с картинками, сортируем (например, по фамилии)
    employees_queryset = EmployeeProfile.objects.prefetch_related(
        Prefetch('images', queryset=EmployeeImage.objects.order_by('position', 'id'))
    ).order_by('last_name', 'first_name')
    
    # Вычисляем стаж в днях для всех сотрудников в списке
    today = timezone.now().date()
    for emp in employees_queryset:
        emp.experience_days = (today - emp.date_joined).days

    # 1. Настройка пагинации по 10 сотрудников на страницу
    paginator = Paginator(employees_queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'title': 'Список сотрудников', 
        'page_obj': page_obj  # Шаблон теперь будет итерировать page_obj вместо employees
    }
    return render(request, 'employees/list.html', context)


@login_required
def employee_detail_view(request, pk):
    """Подробная карточка сотрудника (только для авторизованных)."""
    # Загружаем сотрудника со связанными данными
    employee = get_object_or_404(
        EmployeeProfile.objects.prefetch_related(
            Prefetch('images', queryset=EmployeeImage.objects.order_by('position', 'id'))
        ), 
        pk=pk
    )
    
    skills = employee.employeeskill_set.all()
    all_images = list(employee.images.all())
    
    # Вычисляем стаж в днях
    today = timezone.now().date()
    employee.experience_days = (today - employee.date_joined).days
    
    # Разделяем изображения по требованию задания
    main_image = all_images[0] if all_images else None  # Заглавное фото (первое)
    gallery_images = all_images[1:] if len(all_images) > 1 else []  # Остальные фото (без первого)

    context = {
        'employee': employee, 
        'skills': skills, 
        'main_image': main_image,        # Передаем первое фото отдельно
        'gallery_images': gallery_images  # Передаем галерею без первого фото
    }
    return render(request, 'employees/detail.html', context)


def logout_view(request):
    """Кастомное представление для безопасного выхода пользователя."""
    logout(request)
    return redirect('employees:index')
# =====================================================================
# 2. ДОБАВЛЯЕМ БАЗОВЫЙ VIEWSET В КОНЕЦ ФАЙЛА
# =====================================================================


class EmployeePagination(PageNumberPagination):
    page_size = 10  # Строго 10 сотрудников на страницу

class EmployeeViewSet(viewsets.ViewSet):
    """
    Базовый API ViewSet для управления профилями сотрудников.
    Включает пагинацию, фильтрацию и разграничение прав доступа.
    """
    pagination_class = EmployeePagination
    permission_classes = [EmployeePermission]

    # №1 Получение списка всех сотрудников (с пагинацией и фильтрами)
    def list(self, request):
        # Оптимизируем запросы с prefetch_related на основе вашей ManyToMany связи
        queryset = EmployeeProfile.objects.prefetch_related('images', 'employeeskill_set__skill').all()

        # Фильтрация по навыкам (Пример: ?skills=python,django или по ID: ?skills=1,2)
        skills_param = request.query_params.get('skills')
        if skills_param:
            skills_list = [s.strip() for s in skills_param.split(',')]
            # Проверяем, переданы ли ID или строки
            if skills_list[0].isdigit():
                queryset = queryset.filter(skills__id__in=skills_list).distinct()
            else:
                queryset = queryset.filter(skills__name__icontains__in=skills_list).distinct()

        # Фильтрация по стажу в днях (Пример: ?experience_days=365 — покажет тех, у кого стаж НЕ МЕНЕЕ 365 дней)
        exp_days = request.query_params.get('experience_days')
        if exp_days:
            try:
                today = timezone.now().date()
                max_date = today - timezone.timedelta(days=int(exp_days))
                # date_joined <= max_date означает, что сотрудник устроился раньше этой даты (стаж больше)
                queryset = queryset.filter(date_joined__lte=max_date)
            except ValueError:
                pass

        # Применяем пагинацию
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = EmployeeProfileSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = EmployeeProfileSerializer(queryset, many=True)
        return Response(serializer.data)

    # №2 Получение подробной информации о сотруднике (Личное дело)
    def retrieve(self, request, pk=None):
        employee = get_object_or_404(
            EmployeeProfile.objects.prefetch_related('images', 'employeeskill_set__skill'), 
            pk=pk
        )
        serializer = EmployeeProfileSerializer(employee)
        return Response(serializer.data)

    # №3 Добавление информации о сотруднике (Только Администратор)
    def create(self, request):
        serializer = EmployeeProfileSerializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                # Перехватываем ValidationError из модели (например, правила рассадки за столы)
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # №4 Изменение информации о сотруднике (Только Администратор)
    def update(self, request, pk=None):
        employee = get_object_or_404(EmployeeProfile, pk=pk)
        serializer = EmployeeProfileSerializer(employee, data=request.data)
        if serializer.is_valid():
            try:
                serializer.save()
                return Response(serializer.data)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        employee = get_object_or_404(EmployeeProfile, pk=pk)
        serializer = EmployeeProfileSerializer(employee, data=request.data, partial=True)
        if serializer.is_valid():
            try:
                serializer.save()
                return Response(serializer.data)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # №5 Удаление информации о сотруднике (Только Администратор)
    def destroy(self, request, pk=None):
        employee = get_object_or_404(EmployeeProfile, pk=pk)
        employee.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # Дополнительно: Перемещение между столами (Доступно Смотрителю и Администратору)
    # POST /api/employees/<id>/move_desk/ -> {"desk_number": 5}
    @action(detail=True, methods=['post'], permission_classes=[IsWatcherOrAdmin])
    def move_desk(self, request, pk=None):
        employee = get_object_or_404(EmployeeProfile, pk=pk)
        new_desk = request.data.get('desk_number')
        
        if new_desk is None:
            return Response({'desk_number': 'Это поле обязательно.'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            employee.desk_number = int(new_desk)
            employee.save() # Здесь сработает ваша валидация clean() на проверку соседства столов!
            return Response({
                'status': 'Успешно',
                'message': f'Сотрудник {employee.first_name} перемещен за стол №{new_desk}'
            })
        except ValueError:
            return Response({'desk_number': 'Должно быть целым числом.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
