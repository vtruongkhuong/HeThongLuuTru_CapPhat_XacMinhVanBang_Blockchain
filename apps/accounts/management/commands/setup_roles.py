from django.core.management.base import BaseCommand
from apps.accounts.models import Role

class Command(BaseCommand):
    help = 'Khởi tạo và đồng bộ các vai trò (Role) theo chuẩn thiết kế H3 (Chốt D4)'

    def handle(self, *args, **kwargs):
        # 1. Danh sách 5 role CHUẨN theo thiết kế
        # Lưu ý: Code vẫn giữ là 'admin' để không làm lỗi các file cấu hình views.py và base_5.py trước đó
        roles_data = [
            {
                'code': 'officer_a',
                'name': 'Cán bộ nhập liệu (Maker)',
                'description': 'Import danh sách sinh viên, kết xuất PDF và trình duyệt đợt'
            },
            {
                'code': 'officer_b',
                'name': 'Cán bộ phê duyệt (Checker)',
                'description': 'Đối chiếu dữ liệu gốc và phê duyệt/từ chối đợt tốt nghiệp (Four-eyes)'
            },
            {
                'code': 'issuer',
                'name': 'Người phát hành Web3',
                'description': 'Sử dụng ví Web3 ký số giao dịch và phát hành văn bằng lên Blockchain'
            },
            {
                'code': 'admin', 
                'name': 'Quản trị viên (Super Admin)',
                'description': 'Super Admin - Quản lý tài khoản, phân quyền và cấu hình hệ thống'
            },
            {
                'code': 'student',
                'name': 'Sinh viên',
                'description': 'Đăng nhập cổng Student Portal để tra cứu văn bằng cá nhân'
            }
        ]

        self.stdout.write(self.style.WARNING('Bắt đầu đồng bộ danh sách Role...'))

        # 2. Tạo mới hoặc Cập nhật role chuẩn
        for data in roles_data:
            role, created = Role.objects.update_or_create(
                code=data['code'],
                defaults={
                    'name': data['name'],
                    'description': data['description']
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'[+] Đã tạo mới: {role.name} ({role.code})'))
            else:
                self.stdout.write(self.style.NOTICE(f'[*] Đã cập nhật: {role.name} ({role.code})'))

        # 3. Dọn dẹp rác: Xóa các role cũ không còn nằm trong thiết kế
        obsolete_roles = ['academic_staff', 'reviewer', 'approver']
        deleted_count, _ = Role.objects.filter(code__in=obsolete_roles).delete()
        
        if deleted_count > 0:
            self.stdout.write(self.style.ERROR(f'[-] Đã xóa {deleted_count} role cũ/thừa khỏi hệ thống.'))

        self.stdout.write(self.style.SUCCESS('Hoàn tất khởi tạo và dọn dẹp Role theo chuẩn H3!'))