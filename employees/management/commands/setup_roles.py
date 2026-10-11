from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group

class Command(BaseCommand):
    help = 'Автоматическое создание групп Администратор/Смотритель и тестовых пользователей'

    def handle(self, *args, **kwargs):
        # 1. Создаем группы (названия должны строго совпадать с permissions.py)
        admin_group, created = Group.objects.get_or_create(name='Администратор')
        watcher_group, created = Group.objects.get_or_create(name='Смотритель')
        self.stdout.write(self.style.SUCCESS('Группы "Администратор" и "Смотритель" успешно проверены/созданы.'))

        # 2. Создаем тестового Администратора (если его нет)
        admin_user, created = User.objects.get_or_create(
            username='api_admin', 
            email='admin@company.com'
        )
        if created:
            admin_user.set_password('AdminPass123!')
            admin_user.save()
        admin_user.groups.add(admin_group)
        self.stdout.write(self.style.SUCCESS('Пользователь "api_admin" (пароль: AdminPass123!) добавлен в группу Администраторы.'))

        # 3. Создаем тестового Смотрителя (если его нет)
        watcher_user, created = User.objects.get_or_create(
            username='api_watcher', 
            email='watcher@company.com'
        )
        if created:
            watcher_user.set_password('WatcherPass123!')
            watcher_user.save()
        watcher_user.groups.add(watcher_group)
        self.stdout.write(self.style.SUCCESS('Пользователь "api_watcher" (пароль: WatcherPass123!) добавлен в группу Смотрители.'))

        # 4. Создаем обычного Посетителя (без групп)
        guest_user, created = User.objects.get_or_create(
            username='api_guest', 
            email='guest@company.com'
        )
        if created:
            guest_user.set_password('GuestPass123!')
            guest_user.save()
        self.stdout.write(self.style.SUCCESS('Пользователь "api_guest" (пароль: GuestPass123!) успешно создан (Посетитель).'))
