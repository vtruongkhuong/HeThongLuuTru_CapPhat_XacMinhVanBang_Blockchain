from django.core.management.base import BaseCommand
from apps.accounts.models import Role

class Command(BaseCommand):
    help = 'Khởi tạo các vai trò (Role) cơ bản cho hệ thống phân quyền 6 tác nhân'

    def handle(self, *args, **kwargs):
        # Danh sách các role cần khởi tạo dựa trên thiết kế của bạn
        roles_data = [
            {
                'code': 'officer_a',
                'name': 'Cán bộ nhập liệu',
                'description': 'Import danh sách sinh viên, kết xuất PDF và gửi yêu cầu'
            },
            {
                'code': 'officer_b',
                'name': 'Cán bộ phê duyệt',
                'description': 'Đối chiếu dữ liệu gốc và phê duyệt/từ chối các đợt tốt nghiệp'
            },
            {
                'code': 'issuer',
                'name': 'Người phát hành Web3',
                'description': 'Sử dụng ví Web3 ký số giao dịch và phát hành văn bằng lên Blockchain'
            },
            {
                'code': 'academic_staff',
                'name': 'Cán bộ đào tạo (Tổng hợp)',
                'description': 'Quản lý danh mục khoa, ngành, và các nghiệp vụ đào tạo chung'
            },
            {
                'code': 'admin',
                'name': 'Quản trị viên hệ thống',
                'description': 'Super Admin - Quản lý tài khoản, cấu hình danh mục và hệ thống'
            }
        ]

        self.stdout.write(self.style.WARNING('Bắt đầu kiểm tra và tạo Role...'))

        for data in roles_data:
            # get_or_create giúp kiểm tra: nếu code đã tồn tại thì bỏ qua, chưa có thì tạo mới
            role, created = Role.objects.get_or_create(
                code=data['code'],
                defaults={
                    'name': data['name'],
                    'description': data['description']
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'[+] Đã tạo mới: {role.name} ({role.code})'))
            else:
                self.stdout.write(self.style.NOTICE(f'[*] Đã tồn tại: {role.name} ({role.code})'))

        self.stdout.write(self.style.SUCCESS('Hoàn tất khởi tạo dữ liệu Vai trò (Role)!'))