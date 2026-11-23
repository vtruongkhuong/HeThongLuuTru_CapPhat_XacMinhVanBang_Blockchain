from django.test import TestCase, override_settings
from django.core import mail
from django.utils import timezone
from datetime import timedelta
from apps.degrees.models import Degree
from apps.academic.models import DegreeType, Major, Faculty
from apps.graduation.models import GraduationBatch
from apps.students.models import Student
from apps.student_portal.models import StudentProfileShareLink
from apps.degrees.email_service import (
    send_degree_issued_email,
    send_degree_revoked_email,
    send_share_link_email
)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class EmailServiceTests(TestCase):
    def setUp(self):
        mail.outbox.clear()
        self.faculty = Faculty.objects.create(
            code="F_CNTT",
            name="Khoa Công nghệ thông tin"
        )
        self.degree_type = DegreeType.objects.create(
            code="KS",
            name="Kỹ Sư",
            level="Đại học"
        )
        self.major = Major.objects.create(
            code="KTPM",
            name="Kỹ thuật phần mềm",
            faculty=self.faculty,
            degree_type=self.degree_type
        )
        self.student = Student.objects.create(
            student_code="SV_TEST_EMAIL",
            full_name="Nguyễn Văn Email Test",
            national_id="079201999999",
            email="student.test@ctuet.edu.vn",
            faculty=self.faculty,
            major=self.major
        )
        self.batch = GraduationBatch.objects.create(
            name="Đợt tốt nghiệp Test Email 2026",
            decision_no="QD-EMAIL/2026",
            decision_date=timezone.now().date(),
            degree_type=self.degree_type
        )
        self.degree = Degree.objects.create(
            student=self.student,
            batch=self.batch,
            degree_type=self.degree_type,
            classification="Xuất sắc",
            status="DRAFT",
            canonical_hash="0x" + "a" * 64,
            template_version="v2",
            credential_version="1.0"
        )

    def test_send_degree_issued_email(self):
        """Kiểm tra gửi email chúc mừng cấp bằng thành công"""
        mail.outbox.clear()
        sent = send_degree_issued_email(self.degree)
        self.assertTrue(sent)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn("cấp phát thành công", email.subject)
        self.assertEqual(email.to, [self.student.email])
        self.assertIn(self.student.full_name, email.body)

    def test_send_degree_revoked_email(self):
        """Kiểm tra gửi email cảnh báo thu hồi văn bằng"""
        mail.outbox.clear()
        sent = send_degree_revoked_email(self.degree, reason="Thu hồi do phát hiện sai sót dữ liệu tuyển sinh")
        self.assertTrue(sent)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn("thu hồi", email.subject.lower())
        self.assertEqual(email.to, [self.student.email])
        self.assertIn("sai sót dữ liệu", email.body)

    def test_send_share_link_email(self):
        """Kiểm tra gửi email thông báo tạo link chia sẻ hồ sơ"""
        mail.outbox.clear()
        link = StudentProfileShareLink.objects.create(
            student=self.student,
            token="share-test-token-789",
            label="CV Ứng tuyển Viettel",
            expires_at=timezone.now() + timedelta(days=7),
            days_valid=7
        )
        sent = send_share_link_email(self.student, link, "http://127.0.0.1:8000/portal/share/share-test-token-789/")
        self.assertTrue(sent)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn("liên kết chia sẻ", email.subject.lower())
        self.assertEqual(email.to, [self.student.email])
        self.assertIn("Viettel", email.body)

    def test_degree_signals_trigger(self):
        """Kiểm tra Signal tự động bắt sự kiện đổi trạng thái sang ISSUED và REVOKED"""
        mail.outbox.clear()
        # Chuyển sang ISSUED
        self.degree.status = 'ISSUED'
        self.degree.save()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("cấp phát thành công", mail.outbox[0].subject)

        # Chuyển sang REVOKED
        self.degree.status = 'REVOKED'
        self.degree.save()
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn("thu hồi", mail.outbox[1].subject.lower())
