"""
Chạy: python manage.py seed_roles

Tạo sẵn các Role + Permission mặc định cho hệ thống, để không phải khai
báo tay qua admin mỗi lần setup môi trường mới.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import Role, Permission, RolePermission


PERMISSIONS = [
    ('student.import', 'Import danh sách sinh viên'),
    ('student.view', 'Xem thông tin sinh viên'),
    ('graduation.create_batch', 'Tạo đợt tốt nghiệp'),
    ('graduation.close_batch', 'Đóng đợt tốt nghiệp'),
    ('degree.generate', 'Sinh văn bằng (PDF)'),
    ('degree.review', 'Thẩm định văn bằng'),
    ('degree.approve', 'Duyệt phát hành văn bằng'),
    ('degree.issue', 'Gửi giao dịch phát hành lên blockchain'),
    ('blockchain.retry', 'Gửi lại giao dịch blockchain thất bại'),
    ('revocation.request', 'Yêu cầu thu hồi văn bằng'),
    ('revocation.approve', 'Duyệt thu hồi văn bằng'),
    ('audit.view', 'Xem nhật ký audit'),
    ('report.view', 'Xem báo cáo thống kê'),
]

ROLES = {
    'admin': {
        'name': 'Quản trị hệ thống',
        'permissions': [code for code, _ in PERMISSIONS],  # full quyền
    },
    'academic_staff': {
        'name': 'Cán bộ đào tạo',
        'permissions': [
            'student.import', 'student.view',
            'graduation.create_batch', 'graduation.close_batch',
            'degree.generate',
        ],
    },
    'reviewer': {
        'name': 'Người thẩm định',
        'permissions': ['degree.review', 'student.view'],
    },
    'approver': {
        'name': 'Người duyệt phát hành',
        'permissions': ['degree.approve', 'revocation.approve', 'student.view'],
    },
    'issuer': {
        'name': 'Người phát hành (ký giao dịch blockchain)',
        'permissions': ['degree.issue', 'blockchain.retry'],
    },
    'viewer': {
        'name': 'Chỉ xem / báo cáo',
        'permissions': ['student.view', 'report.view', 'audit.view'],
    },
}


class Command(BaseCommand):
    help = "Seed các Role và Permission mặc định cho hệ thống."

    @transaction.atomic
    def handle(self, *args, **options):
        perm_objs = {}
        for code, name in PERMISSIONS:
            perm, created = Permission.objects.get_or_create(
                code=code, defaults={'name': name}
            )
            perm_objs[code] = perm
            if created:
                self.stdout.write(self.style.SUCCESS(f"  + Permission: {code}"))

        for role_code, data in ROLES.items():
            role, created = Role.objects.get_or_create(
                code=role_code, defaults={'name': data['name']}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"+ Role: {role_code}"))

            for perm_code in data['permissions']:
                RolePermission.objects.get_or_create(
                    role=role, permission=perm_objs[perm_code]
                )

        self.stdout.write(self.style.SUCCESS("Seed roles & permissions hoàn tất."))
