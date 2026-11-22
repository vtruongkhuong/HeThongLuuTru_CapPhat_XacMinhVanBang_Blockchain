from datetime import date
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import transaction

from apps.accounts.models import Role
from apps.academic.models import Faculty, Major, DegreeType
from apps.students.models import Student, ImportBatch, ImportBatchItem
from apps.graduation.models import GraduationBatch
from apps.degrees.models import Degree
from apps.revocation.models import RevocationRequest, ReasonCode
from apps.verification.models import VerificationLog
from apps.api.models import APIClient

User = get_user_model()


class Command(BaseCommand):
    help = 'Khởi tạo dữ liệu demo: Khoa, Ngành, 4 Loại văn bằng/chứng chỉ, 20 Sinh viên và 5 Role Users'

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

        # --- 3. TẠO 4 LOẠI VĂN BẰNG / CHỨNG CHỈ ---
        self.stdout.write(self.style.WARNING('3. Khởi tạo 4 Loại văn bằng & chứng chỉ chuẩn...'))
        deg_ks, _ = DegreeType.objects.update_or_create(
            code='KS',
            defaults={
                'name': 'Bằng Kỹ sư',
                'level': 'Đại học',
                'template_name': 'engineer_degree.html',
                'is_active': True
            }
        )
        deg_cn, _ = DegreeType.objects.update_or_create(
            code='CN',
            defaults={
                'name': 'Bằng Cử nhân',
                'level': 'Đại học',
                'template_name': 'bachelor_degree.html',
                'is_active': True
            }
        )
        deg_thvp, _ = DegreeType.objects.update_or_create(
            code='THVP',
            defaults={
                'name': 'Chứng chỉ Tin học văn phòng',
                'level': 'Chứng chỉ',
                'template_name': 'office_it_cert.html',
                'is_active': True
            }
        )
        deg_cntt, _ = DegreeType.objects.update_or_create(
            code='CNTT',
            defaults={
                'name': 'Chứng chỉ Công nghệ thông tin',
                'level': 'Chứng chỉ',
                'template_name': 'it_specialist_cert.html',
                'is_active': True
            }
        )
        self.stdout.write(self.style.SUCCESS('   [+] 4 Loại bằng/chứng chỉ: KS, CN, THVP, CNTT'))

        # --- 4. TẠO KHOA, NGÀNH ---
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

        old_ktpm = Major.objects.filter(code='KTPM').first()
        if old_ktpm:
            Student.objects.filter(major=old_ktpm).update(major=maj_se)
            old_ktpm.delete()

        majors_cycle = [(fac_it, maj_se), (fac_it, maj_cs), (fac_eco, maj_ba)]

        # --- 5. TẠO ĐỢT TỐT NGHIỆP DRAFT ---
        self.stdout.write(self.style.WARNING('4. Khởi tạo Đợt tốt nghiệp & 20 Sinh viên demo...'))
        batch, _ = GraduationBatch.objects.update_or_create(
            name='Đợt 1 - Tốt nghiệp Năm 2026',
            defaults={
                'decision_no': '2026/QĐ-ĐHKTCN',
                'decision_date': date(2026, 6, 30),
                'status': 'DRAFT',
                'maker': created_users.get('officer_a')
            }
        )

        # --- 6. TẠO IMPORT BATCH ---
        import_batch, _ = ImportBatch.objects.update_or_create(
            batch=batch,
            file_name='Danh_sach_sinh_vien_tot_nghiep_2026.xlsx',
            defaults={
                'imported_by': created_users['officer_a'],
                'mode': 'ATOMIC',
                'inserted': 20,
                'updated': 0,
                'skipped': 0,
                'errors': 0,
            }
        )

        # --- 7. TẠO 20 SINH VIÊN DEMO ---
        sample_names = [
            ("Nguyễn Văn An", "M"), ("Trần Thị Bích", "F"), ("Lê Hoàng Cường", "M"), ("Phạm Minh Đức", "M"),
            ("Hoàng Thị Em", "F"), ("Đỗ Quốc Gia", "M"), ("Vũ Thu Hà", "F"), ("Bùi Trọng Khang", "M"),
            ("Đặng Ngọc Lan", "F"), ("Mai Văn Minh", "M"), ("Ngô Thị Nga", "F"), ("Dương Quang Oanh", "F"),
            ("Lý Thành Phát", "M"), ("Hồ Như Quỳnh", "F"), ("Võ Tấn Sang", "M"), ("Trịnh Văn Thắng", "M"),
            ("Phan Thị Uyên", "F"), ("Đinh Công Vinh", "M"), ("Cao Xuân Yến", "F"), ("Lương Gia Bảo", "M")
        ]

        for i, (name, gender) in enumerate(sample_names, start=1):
            s_code = f"B22{i:05d}"
            fac, maj = majors_cycle[(i - 1) % len(majors_cycle)]

            user_for_sv = created_users['student'] if i == 1 else None
            if user_for_sv:
                # Gỡ user khỏi bất kỳ sinh viên nào khác đang giữ user này để không vi phạm OneToOne unique constraint
                Student.objects.filter(user=user_for_sv).exclude(student_code=s_code).update(user=None)

            sv_email = f"sv{i:03d}@student.edu.vn"
            # Nếu email này đang bị trùng bởi sinh viên có mã khác trong DB, dọn dẹp để tránh đụng unique email
            Student.objects.filter(email=sv_email).exclude(student_code=s_code).delete()

            student, _ = Student.objects.update_or_create(
                student_code=s_code,
                defaults={
                    'full_name': name,
                    'gender': gender,
                    'date_of_birth': date(2004, (i % 12) + 1, (i * 2 % 28) + 1),
                    'national_id': f"092204{i:06d}",
                    'email': sv_email,
                    'phone_number': f"091234{i:04d}",
                    'faculty': fac,
                    'major': maj,
                    'enrollment_year': 2022,
                    'gpa_score': round(2.8 + (i * 0.06), 2),
                    'status': 'draft',
                    'user': user_for_sv
                }
            )

            ImportBatchItem.objects.update_or_create(
                import_batch=import_batch,
                student_code=s_code,
                defaults={
                    'row_number': i + 1,
                    'action': 'INSERT',
                    'new_value': {
                        'full_name': name,
                        'student_code': s_code,
                        'major_code': maj.code,
                        'gpa_score': student.gpa_score
                    }
                }
            )

        self.stdout.write(self.style.SUCCESS('   [+] Đã tạo thành công 20 Sinh viên và gắn vào ImportBatch'))

        # --- 8. TẠO 4 VĂN BẰNG DEMO ON-CHAIN (STATUS='ISSUED') (Task 14) ---
        self.stdout.write(self.style.WARNING('5. Khởi tạo 4 Văn bằng phát hành On-Chain (ISSUED)...'))
        import hashlib, uuid as uuid_lib
        from django.utils import timezone as dj_tz

        issued_students = Student.objects.filter(student_code__in=['B2200001', 'B2200002', 'B2200003', 'B2200004'])
        created_degrees = []
        for idx, st in enumerate(issued_students, start=1):
            deg_hash = hashlib.sha256(f"CTUT-2026-DEMO-{st.student_code}-{idx}".encode()).hexdigest()
            deg, _ = Degree.objects.update_or_create(
                student=st,
                batch=batch,
                defaults={
                    'degree_type': st.major.degree_type or deg_ks,
                    'credential_public_id': uuid_lib.uuid5(uuid_lib.NAMESPACE_DNS, f"ctut.degree.{st.student_code}"),
                    'classification': 'Giỏi' if idx % 2 == 1 else 'Khá',
                    'issue_date': date(2026, 7, 1),
                    'template_version': 'v2.0',
                    'credential_version': '1.0',
                    'canonical_hash': deg_hash,
                    'status': 'ISSUED',
                    'generated_at': dj_tz.now(),
                    'approved_by': created_users.get('officer_b'),
                    'reviewed_by': created_users.get('officer_a'),
                }
            )
            created_degrees.append(deg)
            self.stdout.write(self.style.SUCCESS(f'   [+] Degree ISSUED: {st.full_name} ({st.student_code}) - {deg.credential_public_id}'))

        # --- 9. TẠO 1 VĂN BẰNG BỊ THU HỒI (STATUS='REVOKED') (Task 14) ---
        self.stdout.write(self.style.WARNING('6. Khởi tạo 1 Văn bằng bị thu hồi (REVOKED)...'))
        st_revoked = Student.objects.filter(student_code='B2200005').first()
        if st_revoked:
            rev_hash = hashlib.sha256(f"CTUT-2026-REVOKED-{st_revoked.student_code}".encode()).hexdigest()
            deg_rev, _ = Degree.objects.update_or_create(
                student=st_revoked,
                batch=batch,
                defaults={
                    'degree_type': st_revoked.major.degree_type or deg_ks,
                    'credential_public_id': uuid_lib.uuid5(uuid_lib.NAMESPACE_DNS, f"ctut.degree.{st_revoked.student_code}"),
                    'classification': 'Trung bình',
                    'issue_date': date(2026, 7, 1),
                    'template_version': 'v2.0',
                    'credential_version': '1.0',
                    'canonical_hash': rev_hash,
                    'status': 'REVOKED',
                    'generated_at': dj_tz.now(),
                    'approved_by': created_users.get('officer_b'),
                    'reviewed_by': created_users.get('officer_a'),
                }
            )
            reason = ReasonCode.objects.filter(code='DISCIPLINARY').first() or ReasonCode.objects.first()
            if reason:
                RevocationRequest.objects.update_or_create(
                    degree=deg_rev,
                    defaults={
                        'reason_code': reason,
                        'description': 'Thu hồi do phát hiện vi phạm quy chế tuyển sinh & kỷ luật sinh viên.',
                        'status': 'EXECUTED',
                        'requested_by': created_users.get('officer_a'),
                        'approved_by': created_users.get('officer_b'),
                        'executed_by': created_users.get('issuer'),
                        'requested_at': dj_tz.now(),
                        'approved_at': dj_tz.now(),
                        'executed_at': dj_tz.now(),
                    }
                )
            self.stdout.write(self.style.SUCCESS(f'   [+] Degree REVOKED: {st_revoked.full_name} ({st_revoked.student_code})'))

        # --- 10. TẠO 10 VERIFICATION LOGS MẪU CHO BIỂU ĐỒ & LỊCH SỬ (Task 14) ---
        self.stdout.write(self.style.WARNING('7. Khởi tạo 10 Lịch sử tra cứu VerificationLog...'))
        log_samples = [
            ('CTUT-2026-000001', created_degrees[0] if created_degrees else None, 'VALID', True),
            ('CTUT-2026-000002', created_degrees[1] if len(created_degrees) > 1 else None, 'VALID', True),
            ('CTUT-2026-000003', created_degrees[2] if len(created_degrees) > 2 else None, 'VALID', True),
            ('CTUT-2026-000005', deg_rev if 'deg_rev' in locals() else None, 'REVOKED', True),
            ('CTUT-FAKE-999999', None, 'TAMPERED', False),
            ('CTUT-FAKE-888888', None, 'NOT_FOUND', False),
            ('CTUT-2026-000001', created_degrees[0] if created_degrees else None, 'VALID', True),
            ('CTUT-2026-000002', created_degrees[1] if len(created_degrees) > 1 else None, 'VALID', True),
            ('CTUT-FAKE-777777', None, 'TAMPERED', False),
            ('CTUT-2026-000004', created_degrees[3] if len(created_degrees) > 3 else None, 'VALID', True),
        ]
        for query_code, d_obj, res_st, is_succ in log_samples:
            VerificationLog.objects.create(
                search_query=query_code,
                degree=d_obj,
                ip_address='127.0.0.1',
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0',
                is_successful=is_succ,
                result_status=res_st,
                verification_type='PUBLIC_SEARCH',
            )
        self.stdout.write(self.style.SUCCESS('   [+] 10 VerificationLog mẫu (VALID, REVOKED, TAMPERED, NOT_FOUND)'))

        # --- 11. TẠO APICLIENT MẪU CHO DOANH NGHIỆP DEMO (Task 14) ---
        self.stdout.write(self.style.WARNING('8. Khởi tạo Doanh nghiệp API Client demo...'))
        demo_key = "4397dc03eec1bbc03d28b37c81540f537e072324af958bb7dd74acde8699da11"
        api_client, _ = APIClient.objects.update_or_create(
            api_key=demo_key,
            defaults={
                'name': "Tập Đoàn Công Nghệ FPT - Ban Tuyển Dụng",
                'is_active': True,
                'quota_per_day': 500,
                'usage_today': 5,
                'contact_email': 'hr-tuyendung@fpt.com.vn',
            }
        )
        self.stdout.write(self.style.SUCCESS(f'   [+] API Client: {api_client.name} | Key: {demo_key[:12]}...'))

        self.stdout.write(self.style.SUCCESS('\n=== ✅ SEED DATA DEMO HOÀN TẤT THÀNH CÔNG ==='))
