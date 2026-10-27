from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
import uuid

from apps.workflow.services import transition, ensure_different_actors, VALID_TRANSITIONS
from apps.degrees.models import Degree
from apps.academic.models import DegreeType, Faculty, Major
from apps.students.models import Student
from apps.graduation.models import GraduationBatch

User = get_user_model()


class WorkflowServiceTests(TestCase):
    """Kiểm thử chuyển đổi trạng thái và nguyên tắc 4-eyes của Khương."""

    def setUp(self):
        self.maker = User.objects.create_user(username='maker_user', email='maker@test.com')
        self.checker = User.objects.create_user(username='checker_user', email='checker@test.com')

        self.deg_type = DegreeType.objects.create(code='CN', name='Cử nhân', template_name='bachelor_degree.html')
        self.faculty = Faculty.objects.create(code='CNTT', name='Công nghệ thông tin')
        self.major = Major.objects.create(code='7480201', name='Công nghệ thông tin', faculty=self.faculty, degree_type=self.deg_type)
        self.student = Student.objects.create(
            student_code='B210001',
            full_name='Trần Văn B',
            faculty=self.faculty,
            major=self.major
        )
        self.batch = GraduationBatch.objects.create(name='Đợt 1 2026', maker=self.maker)
        
        self.degree = Degree.objects.create(
            student=self.student,
            batch=self.batch,
            degree_type=self.deg_type,
            credential_public_id=uuid.uuid4(),
            canonical_hash='0x' + '1' * 64,
            status='DRAFT'
        )

    def test_ensure_different_actors_violation(self):
        """Báo lỗi ValidationError khi 1 người làm cả Maker và Checker."""
        with self.assertRaises(ValidationError):
            ensure_different_actors(self.maker, self.maker)

    def test_ensure_different_actors_valid(self):
        """Hợp lệ khi 2 người khác nhau."""
        self.assertTrue(ensure_different_actors(self.maker, self.checker))

    def test_transition_flow_draft_to_reviewed(self):
        """Chuyển trạng thái DRAFT -> REVIEWED thành công."""
        updated = transition(self.degree, 'REVIEWED', actor=self.maker)
        self.assertEqual(updated.status, 'REVIEWED')
        self.assertEqual(updated.reviewed_by, self.maker)

    def test_transition_flow_reviewed_to_approved_4_eyes(self):
        """Phê duyệt REVIEWED -> APPROVED yêu cầu người duyệt khác người trình."""
        self.degree.status = 'REVIEWED'
        self.degree.reviewed_by = self.maker
        self.degree.save()

        # Nếu maker tự duyệt -> Báo lỗi 4-eyes
        with self.assertRaises(ValidationError):
            transition(self.degree, 'APPROVED', actor=self.maker)

        # Checker khác duyệt -> Thành công
        updated = transition(self.degree, 'APPROVED', actor=self.checker)
        self.assertEqual(updated.status, 'APPROVED')
        self.assertEqual(updated.approved_by, self.checker)

    def test_invalid_transition_rejected(self):
        """Chuyển trạng thái không hợp lệ (ví dụ: DRAFT nhảy cóc sang ISSUED) bị chặn."""
        with self.assertRaises(ValidationError):
            transition(self.degree, 'ISSUED', actor=self.checker)
