from django.test import TestCase
from django.core.exceptions import ValidationError
from django.urls import reverse
from .models import EmployeeProfile, Skill, EmployeeSkill
from django.contrib.auth.models import User, Group
from rest_framework import status
from rest_framework.test import APITestCase


class EmployeeSystemComprehensiveUnitTest(TestCase):
    """Набор тестов на базе Django Unittest для проверки адресов, контекста и валидатора."""

    def setUp(self):
        """Подготовка изолированной базы данных перед запуском каждого теста."""
        # Создаем учетные записи для проверки прав доступа
        self.user_dev = User.objects.create_user(username="dev_user", password="secure_pass_123")
        self.user_tester = User.objects.create_user(username="test_user", password="secure_pass_123")
        self.user_guest = User.objects.create_user(username="guest_user", password="secure_pass_123")

        # Создаем базовый профиль разработчика для проверки адресов и контекста
        self.emp_developer = EmployeeProfile.objects.create(
            user=self.user_dev,
            first_name="Алексей",
            last_name="Разработчиков",
            gender="M",
            role="backend",
            desk_number=10
        )

        # Создаем навык и привязываем его к сотруднику
        self.skill_django = Skill.objects.create(name="Django Framework")
        EmployeeSkill.objects.create(employee=self.emp_developer, skill=self.skill_django, level=9)

    # =========================================================================
    # 1. ТЕСТИРОВАНИЕ АДРЕСОВ (URLS) И ПРАВ ДОСТУПА
    # =========================================================================
    
    def test_public_pages_availability(self):
        """Проверка: Главная страница и Каталог доступны публично (HTTP 200)."""
        # Проверка главной страницы
        response_index = self.client.get(reverse('employees:index'))
        self.assertEqual(response_index.status_code, 200)

        # Проверка страницы списка сотрудников
        response_list = self.client.get(reverse('employees:list'))
        self.assertEqual(response_list.status_code, 200)

    def test_detail_page_blocks_anonymous_user(self):
        """Проверка: Неавторизованный пользователь получает редирект (HTTP 302) с карточки."""
        detail_url = reverse('employees:detail', kwargs={'pk': self.emp_developer.pk})
        response = self.client.get(detail_url)
        
        # Ожидаем перенаправление на страницу входа
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_detail_page_allows_authenticated_user(self):
        """Проверка: Авторизованный пользователь успешно открывает карточку (HTTP 200)."""
        detail_url = reverse('employees:detail', kwargs={'pk': self.emp_developer.pk})
        
        # Симулируем логин пользователя в систему
        self.client.login(username="guest_user", password="secure_pass_123")
        response = self.client.get(detail_url)
        
        self.assertEqual(response.status_code, 200)

    # =========================================================================
    # 2. ТЕСТИРОВАНИЕ СЛОВАРЕЙ КОНТЕКСТА (CONTEXT DATA)
    # =========================================================================

    def test_main_page_context_data(self):
        """Проверка: Контекст Главной страницы содержит счетчик и список со стажем."""
        response = self.client.get(reverse('employees:index'))
        
        # Проверяем наличие ключей в словаре контекста
        self.assertIn('total_employees', response.context)
        self.assertIn('employees', response.context)
        
        # Проверяем корректность значения счетчика
        self.assertEqual(response.context['total_employees'], 1)
        
        # Проверяем, что у объекта сотрудника вычислен стаж в днях
        employee_entry = response.context['employees'][0]
        self.assertTrue(hasattr(employee_entry, 'experience_days'))
        self.assertEqual(employee_entry.experience_days, 0)  # Создан сегодня

    def test_catalog_page_context_has_pagination(self):
        """Проверка: Каталог отдает объект пагинатора (page_obj) вместо прямого QuerySet."""
        response = self.client.get(reverse('employees:list'))
        
        self.assertIn('page_obj', response.context)
        # Проверяем, что элементы внутри пагинатора тоже имеют поле стажа
        self.assertTrue(hasattr(response.context['page_obj'][0], 'experience_days'))

    def test_detail_page_context_structure(self):
        """Проверка: Подробная карточка отдает все разделенные переменные для шаблона."""
        self.client.login(username="guest_user", password="secure_pass_123")
        detail_url = reverse('employees:detail', kwargs={'pk': self.emp_developer.pk})
        response = self.client.get(detail_url)
        
        # Сверяем структуру контекста с ТЗ
        self.assertIn('employee', response.context)
        self.assertIn('skills', response.context)
        self.assertIn('main_image', response.context)
        self.assertIn('gallery_images', response.context)
        
        # Проверяем точечные значения переданных данных
        self.assertEqual(response.context['employee'].pk, self.emp_developer.pk)
        self.assertEqual(response.context['skills'].count(), 1)

    # =========================================================================
    # 3. ТЕСТИРОВАНИЕ РАБОТЫ ВАЛИДАТОРА (БИЗНЕС-ЛОГИКА СТОЛОВ)
    # =========================================================================

    def test_validator_blocks_qa_next_to_developer(self):
        """Проверка: Валидатор пресекает попытку посадить тестировщика за соседний стол."""
        # Бэкендер сидит за 10 столом. Пробуем посадить тестировщика за соседний 11 стол
        bad_qa_profile = EmployeeProfile(
            user=self.user_tester,
            first_name="Петр",
            last_name="Тестировщиков",
            gender="M",
            role="qa",
            desk_number=11
        )
        
        # Unittest должен поймать ValidationError при вызове метода save()
        with self.assertRaises(ValidationError) as error_context:
            bad_qa_profile.save()
            
        # Убеждаемся, что ошибка валидации сработала именно на поле desk_number
        self.assertIn('desk_number', error_context.exception.message_dict)

    def test_validator_allows_safe_distance_desks(self):
        """Проверка: Разрешено сохранение, если столы сотрудников не граничат друг с другом."""
        # Сажаем тестировщика через один стол (на 12-й стол, когда dev сидит за 10-м)
        safe_qa_profile = EmployeeProfile(
            user=self.user_tester,
            first_name="Петр",
            last_name="Тестировщиков",
            gender="M",
            role="qa",
            desk_number=12
        )
        
        # Данная операция не должна вызывать исключений
        try:
            safe_qa_profile.save()
        except ValidationError:
            self.fail("Ошибка! Валидатор ложно заблокировал безопасное расстояние столов (10 и 12).")

from django.contrib.auth.models import User, Group
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import EmployeeProfile, Skill, EmployeeSkill

class EmployeeAPITests(APITestCase):

    def setUp(self):
        """Настройка тестовой базы данных перед каждым тестом"""
        # 1. Создаем группы доступа
        self.admin_group = Group.objects.create(name='Администратор')
        self.watcher_group = Group.objects.create(name='Смотритель')

        # 2. Создаем тестовых пользователей
        self.admin_user = User.objects.create_user(username='admin', password='password123')
        self.admin_user.groups.add(self.admin_group)

        self.watcher_user = User.objects.create_user(username='watcher', password='password123')
        self.watcher_user.groups.add(self.watcher_group)

        self.guest_user = User.objects.create_user(username='guest', password='password123')

        # 3. Создаем базовых пользователей, к которым будем привязывать профили
        self.emp_user_1 = User.objects.create_user(username='emp1', password='password123')
        self.emp_user_2 = User.objects.create_user(username='emp2', password='password123')

        # 4. Создаем существующего сотрудника (Бэкендер за столом №10)
        self.existing_employee = EmployeeProfile.objects.create(
            user=self.emp_user_1,
            first_name="Иван",
            last_name="Разработчиков",
            gender="M",
            role="backend",
            desk_number=10
        )
        
        # URL для списка сотрудников (базовый ViewSet)
        self.list_url = reverse('employees:employee-list')

    def test_list_employees_accessible_by_guest(self):
        """К2: Посетитель (даже без авторизации) может просматривать список"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Проверяем, что в ответе есть ключи пагинации DRF
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)

    def test_create_employee_forbidden_for_watcher(self):
        """К6: Смотритель не имеет прав на создание сотрудника (403 Forbidden)"""
        # Авторизуемся под смотрителем
        self.client.force_authenticate(user=self.watcher_user)
        
        data = {
            "user": self.emp_user_2.id,
            "first_name": "Петр",
            "last_name": "Тестеров",
            "gender": "M",
            "role": "qa",
            "desk_number": 50
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_business_logic_desk_conflict(self):
        """К4: Валидация блокирует посадку тестировщика рядом с разработчиком (400 Bad Request)"""
        # Авторизуемся под администратором
        self.client.force_authenticate(user=self.admin_user)
        
        # Наш существующий бэкендер сидит за столом №10.
        # Пытаемся посадить тестировщика (qa) за соседний стол №11:
        data = {
            "user": self.emp_user_2.id,
            "first_name": "Анна",
            "last_name": "Тестировщикова",
            "gender": "F",
            "role": "qa",
            "desk_number": 11  # Конфликт! Соседний с №10
        }
        
        response = self.client.post(self.list_url, data, format='json')
        # API должно вернуть 400 Bad Request из-за вашей валидации clean()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_create_employee_success(self):
        """Администратор может успешно создать сотрудника, если правила соблюдены"""
        self.client.force_authenticate(user=self.admin_user)
        
        data = {
            "user": self.emp_user_2.id,
            "first_name": "Анна",
            "last_name": "Тестировщикова",
            "gender": "F",
            "role": "qa",
            "desk_number": 50  # Безопасный стол далеко от №10
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
