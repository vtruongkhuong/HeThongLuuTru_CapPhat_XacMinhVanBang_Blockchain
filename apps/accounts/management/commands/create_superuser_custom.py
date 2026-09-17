"""
Chạy: python manage.py create_superuser_custom --username admin --email admin@example.com --password xxx

Tạo superuser VÀ gán luôn Role 'admin' (khác createsuperuser mặc định của
Django, vốn không biết gì về RBAC custom của hệ thống này).
"""
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User, Role, UserRole


class Command(BaseCommand):
    help = "Tạo superuser và gán Role 'admin' trong hệ thống RBAC."

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True)
        parser.add_argument('--email', required=True)
        parser.add_argument('--password', required=True)

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']

        if User.objects.filter(username=username).exists():
            raise CommandError(f"User '{username}' đã tồn tại.")

        user = User.objects.create_superuser(
            username=username, email=email, password=password
        )

        admin_role, _ = Role.objects.get_or_create(
            code='admin', defaults={'name': 'Quản trị hệ thống'}
        )
        UserRole.objects.get_or_create(user=user, role=admin_role)

        self.stdout.write(self.style.SUCCESS(
            f"Đã tạo superuser '{username}' và gán Role 'admin'. "
            f"Lưu ý: chạy 'python manage.py seed_roles' trước để Role có đủ permission."
        ))
