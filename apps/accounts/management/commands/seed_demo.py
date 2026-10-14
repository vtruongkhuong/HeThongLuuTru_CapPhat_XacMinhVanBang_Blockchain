from datetime import date
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import transaction

from apps.accounts.models import Role
from apps.academic.models import Faculty, Major, DegreeType
from apps.students.models import Student, ImportBatch, ImportBatchItem
from apps.graduation.models import GraduationBatch

User = get_user_model()


class Command(BaseCommand):
    help = 'Khởi tạo dữ liệu demo chuẩn H4: Khoa, Ngành, Loại văn bằng, 20 Sinh viên và 5 Role Users'

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('1. Đồng bộ danh sách Roles...'))
        call_command('setup_roles')

        # --- 2. TẠO USER CHO TỪNG ROLE ---
        self.stdout.write(self.style.WARNING('2. Khởi tạo tài khoản cho 5 vai trò...'))
        users_config = [
            {'username': 'superadmin', 'email': 'admin@demo.edu.vn', 'role': 'admin', 'is_staff': True, 'is_superuser': True},
            {'username': 'canbonhaplieu', 'email': 'officera@demo.edu.vn', 'role': 'officer_a', 'is_staff': True, 'is_superuser': False},
            {'username': 'canbopheduyet', 'email': 'officerb@demo.edu.vn', 'role': 'officer_b', 'is_staff': True, 'is_superuser': False},
            {'username': 'canbophathanh', 'email': 'issuer@demo.edu.vn', 'role': 'issuer', 'is_staff': True, 'is_superuser': False},
            {'username': 'sinhvien01', 'email': 'sv001@student.edu.vn', 'role': 'student', 'is_staff': False, 'is_superuser': False},
        ]

        created_users = {}
        for u_data in users_config:
            user, _ = User.objects.update_or_create(
                username=u_data['username'],
                defaults={
                    'email': u_data['email'],
                    'is_staff': u_data['is_staff'],
                    'is_superuser': u_data['is_superuser'],
                }
            )
            user.set_password('Demo@12345')
            user.save()

            role_obj = Role.objects.filter(code=u_data['role']).first()
            if role_obj and hasattr(user, 'roles'):
                user.roles.set([role_obj])
            created_users[u_data['role']] = user
            self.stdout.write(self.style.SUCCESS(f'   [+] {user.username} / Demo@12345 ({u_data["role"]})'))

        # --- 3. TẠO LOẠI VĂN BẰNG, KHOA, NGÀNH ---
        self.stdout.write(self.style.WARNING('3. Khởi tạo Khoa, Ngành và Loại văn bằng...'))
        deg_ks, _ = DegreeType.objects.update_or_create(
            code='KS',
            defaults={
                'name': 'Bằng Kỹ sư',
                'level': 'Đại học',
                'template_name': 'degree_template.html',
                'is_active': True
            }
        )
        deg_cn, _ = DegreeType.objects.update_or_create(
            code='CN',
            defaults={
                'name': 'Bằng Cử nhân',
                'level': 'Đại học',
                'template_name': 'degree_template.html',
                'is_active': True
            }
        )

        fac_it, _ = Faculty.objects.update_or_create(
            code='CNTT',
            defaults={'name': 'Khoa Công nghệ thông tin', 'is_active': True}
        )
        fac_eco, _ = Faculty.objects.update_or_create(
            code='KT',
            defaults={'name': 'Khoa Kinh tế', 'is_active': True}
        )

        maj_se, _ = Major.objects.update_or_create(
            code='7480103',
            defaults={'name': 'Kỹ thuật phần mềm', 'faculty': fac_it, 'degree_type': deg_ks, 'is_active': True}
        )
        maj_cs, _ = Major.objects.update_or_create(
            code='7480201',
            defaults={'name': 'Công nghệ thông tin', 'faculty': fac_it, 'degree_type': deg_ks, 'is_active': True}
        )
        maj_ba, _ = Major.objects.update_or_create(
            code='7340101',
            defaults={'name': 'Quản trị kinh doanh', 'faculty': fac_eco, 'degree_type': deg_cn, 'is_active': True}
        )
        # Tự động chuyển sinh viên từ mã ngành chữ cũ (KTPM) sang mã số chuẩn (7480103) và xóa bản ghi trùng
        old_ktpm = Major.objects.filter(code='KTPM').first()
        if old_ktpm:
            Student.objects.filter(major=old_ktpm).update(major=maj_se)
            old_ktpm.delete()

        majors_cycle = [(fac_it, maj_se), (fac_it, maj_cs), (fac_eco, maj_ba)]

        # --- 4. TẠO 20 SINH VIÊN DEMO ---
        self.stdout.write(self.style.WARNING('4. Khởi tạo 20 hồ sơ sinh viên...'))
        sample_names = [
            "Nguyễn Văn An", "Trần Thị Bình", "Lê Hoàng Cường", "Phạm Minh Dũng", "Hoàng Thị Em",
            "Vũ Đình Phương", "Đặng Thu Giang", "Bùi Quốc Hải", "Đỗ Ngọc Hùng", "Hồ Thị Khánh",
            "Ngô Tuấn Kiệt", "Dương Mỹ Linh", "Lý Hoàng Long", "Phan Thanh Mai", "Trịnh Quốc Nam",
            "Đinh Thảo Nguyên", "Lâm Gia Phong", "Mai Anh Quân", "Tạ Minh Tâm", "Châu Ngọc Trang"
        ]

        students_list = []
        for i in range(1, 21):
            sv_code = f"SV2026{i:03d}"
            fac, maj = majors_cycle[(i - 1) % len(majors_cycle)]
            student, _ = Student.objects.update_or_create(
                student_code=sv_code,
                defaults={
                    'full_name': sample_names[i - 1],
                    'date_of_birth': date(2004, (i % 12) + 1, (i % 28) + 1),
                    'gender': 'M' if i % 2 != 0 else 'F',
                    'national_id': f"09220400{i:04d}",
                    'email': f"sv{i:03d}@student.edu.vn",
                    'phone_number': f"0909123{i:03d}",
                    'faculty': fac,
                    'major': maj,
                    'enrollment_year': 2022,
                    'status': 'approved',
                    'user': created_users['student'] if i == 1 else None,
                }
            )
            students_list.append(student)

        # --- 5. TẠO ĐỢT TỐT NGHIỆP & LỊCH SỬ IMPORT ---
        self.stdout.write(self.style.WARNING('5. Khởi tạo Đợt tốt nghiệp và ImportBatch mẫu...'))
        grad_batch, _ = GraduationBatch.objects.update_or_create(
            name='Đợt tốt nghiệp Demo Tháng 10/2026',
            defaults={'status': 'DRAFT'}
        )

        imp_batch, created_imp = ImportBatch.objects.update_or_create(
            batch=grad_batch,
            file_name='danh_sach_20_sinh_vien_demo.xlsx',
            defaults={
                'imported_by': created_users['officer_a'],
                'mode': 'ATOMIC',
                'inserted': 20,
                'updated': 0,
                'skipped': 0,
                'errors': 0,
            }
        )

        if created_imp:
            items = [
                ImportBatchItem(
                    import_batch=imp_batch,
                    row_number=idx + 1,
                    student_code=st.student_code,
                    action='INSERT',
                    new_value={'full_name': st.full_name, 'major': st.major.code}
                )
                for idx, st in enumerate(students_list)
            ]
            ImportBatchItem.objects.bulk_create(items)

        self.stdout.write(self.style.SUCCESS('\n✅ HOÀN TẤT SEED DỮ LIỆU DEMO (H4)!'))