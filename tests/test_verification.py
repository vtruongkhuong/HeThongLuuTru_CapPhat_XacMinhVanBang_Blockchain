from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from apps.students.models import Student
from apps.degrees.models import Degree
from apps.academic.models import DegreeType, Faculty, Major
from apps.graduation.models import GraduationBatch
import uuid

User = get_user_model()


class StudentPortalTests(TestCase):
    """Kiểm thử đăng nhập bằng Gmail / Email và hiển thị chia 4 danh mục văn bằng."""

    def setUp(self):
        self.client = Client()

        # Tạo khoa, ngành, và 4 loại văn bằng
        self.faculty = Faculty.objects.create(code='CNTT', name='Công nghệ thông tin')
        self.deg_ks = DegreeType.objects.create(code='KS', name='Bằng Kỹ sư', template_name='engineer_degree.html')
        self.deg_cn = DegreeType.objects.create(code='CN', name='Bằng Cử nhân', template_name='bachelor_degree.html')
        self.deg_thvp = DegreeType.objects.create(code='THVP', name='Chứng chỉ Tin học văn phòng', template_name='office_it_cert.html')
        self.deg_cntt = DegreeType.objects.create(code='CNTT', name='Chứng chỉ Công nghệ thông tin', template_name='it_specialist_cert.html')

        self.major = Major.objects.create(code='7480201', name='Công nghệ thông tin', faculty=self.faculty, degree_type=self.deg_ks)

        # Tạo sinh viên với email Gmail
        self.student_email = 'nguyenvana@gmail.com'
        self.student = Student.objects.create(
            student_code='B2200001',
            full_name='Nguyễn Văn A',
            email=self.student_email,
            faculty=self.faculty,
            major=self.major
        )

        # Tạo user tương ứng đăng nhập bằng Gmail
        self.user = User.objects.create_user(
            username='nguyenvana',
            email=self.student_email,
            password='Password@123'
        )

        # Tạo đợt tốt nghiệp
        self.batch = GraduationBatch.objects.create(name='Đợt 1 Năm 2026')

        # Cấp 2 loại văn bằng/chứng chỉ cho sinh viên: 1 Bằng Kỹ sư và 1 Chứng chỉ Tin học VP
        self.deg_1 = Degree.objects.create(
            student=self.student,
            batch=self.batch,
            degree_type=self.deg_ks,
            credential_public_id=uuid.uuid4(),
            canonical_hash='0x' + 'a' * 64,
            status='ISSUED'
        )
        self.deg_2 = Degree.objects.create(
            student=self.student,
            batch=self.batch,
            degree_type=self.deg_thvp,
            credential_public_id=uuid.uuid4(),
            canonical_hash='0x' + 'b' * 64,
            status='ISSUED'
        )

    def test_login_with_gmail_and_access_portal(self):
        """Đăng nhập trực tiếp bằng Gmail và kiểm tra tự động nhận diện sinh viên."""
        # 1. Đăng nhập bằng Gmail
        login_success = self.client.login(username=self.student_email, password='Password@123')
        self.assertTrue(login_success, "Không đăng nhập được bằng email Gmail!")

        # 2. Truy cập Cổng sinh viên
        response = self.client.get('/portal/dashboard/')
        self.assertEqual(response.status_code, 200)

        # Kiểm tra thông tin sinh viên hiển thị
        self.assertContains(response, 'B2200001')
        self.assertContains(response, 'Nguyễn Văn A')
        self.assertContains(response, self.student_email)

        # Kiểm tra 2 danh mục văn bằng có mặt
        self.assertContains(response, 'BẰNG KỸ SƯ CHÍNH QUY')
        self.assertContains(response, 'CHỨNG CHỈ TIN HỌC VĂN PHÒNG')

        # Kiểm tra đếm số lượng văn bằng
        counts = response.context['counts']
        self.assertEqual(counts['all'], 2)
        self.assertEqual(counts['engineer'], 1)
        self.assertEqual(counts['office_it'], 1)
        self.assertEqual(counts['bachelor'], 0)
        self.assertEqual(counts['it_cert'], 0)

    def test_download_pdf_by_degree_id(self):
        """Tải riêng file PDF theo từng ID văn bằng."""
        self.client.login(username=self.student_email, password='Password@123')
        response = self.client.get(f'/portal/tai-van-bang/{self.deg_1.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')


class EmployerSessionAndDuplicateTests(TestCase):
    """Kiểm thử tính năng Lưu phiên kiểm định doanh nghiệp và phát hiện trùng lặp."""

    def setUp(self):
        self.client = Client()
        self.faculty = Faculty.objects.create(code='CNTT_TEST', name='Khoa CNTT')
        self.deg_ks = DegreeType.objects.create(code='KS_TEST', name='Bằng Kỹ Sư')
        self.major = Major.objects.create(code='7480103_T', name='KTPM', faculty=self.faculty, degree_type=self.deg_ks)
        self.student = Student.objects.create(
            student_code='B219999',
            full_name='Lê Văn Test Trùng',
            email='test.trung@ctuet.edu.vn',
            faculty=self.faculty,
            major=self.major
        )
        self.batch = GraduationBatch.objects.create(name='Đợt tốt nghiệp 2026')
        self.degree = Degree.objects.create(
            student=self.student,
            batch=self.batch,
            degree_type=self.deg_ks,
            status='ISSUED',
            canonical_hash='0x' + '9' * 64
        )

    def test_check_duplicate_degree(self):
        """Kiểm tra hàm phát hiện văn bằng trùng lặp"""
        from apps.degrees.services import check_duplicate_degree
        dup = check_duplicate_degree(self.student, self.deg_ks.id)
        self.assertIsNotNone(dup)
        self.assertEqual(dup.id, self.degree.id)

        # Khi văn bằng bị thu hồi (REVOKED), không còn tính là trùng
        self.degree.status = 'REVOKED'
        self.degree.save()
        dup_revoked = check_duplicate_degree(self.student, self.deg_ks.id)
        self.assertIsNone(dup_revoked)

    def test_employer_session_creation_and_history(self):
        """Kiểm tra lưu phiên thẩm định doanh nghiệp và xem lịch sử"""
        from apps.verification.models import EmployerVerificationSession

        session = EmployerVerificationSession.objects.create(
            session_code="HR-20261123-TEST01",
            employer_name="FPT Software",
            recruitment_name="Tuyển dụng Fresher Q4/2026",
            total_checked=10,
            total_verified=8,
            total_tampered=1,
            total_revoked=1,
            total_not_found=0,
            result_detail=[{'student_name': 'Lê Văn Test Trùng', 'status': 'VERIFIED'}]
        )
        self.assertEqual(session.session_code, "HR-20261123-TEST01")
        self.assertEqual(session.employer_name, "FPT Software")

        # Truy cập trang lịch sử phiên
        response = self.client.get('/verify/doanh-nghiep/lich-su/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "HR-20261123-TEST01")
        self.assertContains(response, "FPT Software")

        # Truy cập xem chi tiết phiên
        detail_resp = self.client.get(f'/verify/doanh-nghiep/lich-su/{session.session_code}/')
        self.assertEqual(detail_resp.status_code, 200)
        self.assertContains(detail_resp, "HR-20261123-TEST01")
        self.assertContains(detail_resp, "Tuyển dụng Fresher Q4/2026")
