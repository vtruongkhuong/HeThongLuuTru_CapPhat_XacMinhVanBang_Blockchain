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
