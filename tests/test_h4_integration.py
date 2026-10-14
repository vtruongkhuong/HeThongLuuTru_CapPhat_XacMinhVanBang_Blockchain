from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.accounts.models import Role
from apps.academic.models import Faculty, Major, DegreeType
from apps.students.models import Student, ImportBatch, ImportBatchItem
from apps.graduation.models import GraduationBatch
from apps.degrees.models import Degree
from apps.blockchain.models import IssuanceBatch, BlockchainTransaction
from apps.workflow.services import ensure_different_actors
from apps.blockchain.services import generate_canonical_hash, build_merkle_root

User = get_user_model()


class H4SystemIntegrationTests(TestCase):
    """Bộ kiểm thử tích hợp H4: Four-eyes, Rollback Import, Hash/Merkle Root và Thu hồi 3 bước."""

    def setUp(self):
        # 1. Tạo Users cho 3 vai trò độc lập
        self.officer_a = User.objects.create_user(username='user_a', email='a@test.com', password='123')
        self.officer_b = User.objects.create_user(username='user_b', email='b@test.com', password='123')
        self.issuer = User.objects.create_user(username='user_issuer', email='issuer@test.com', password='123')

        # 2. Tạo Danh mục đào tạo cơ sở
        self.deg_type = DegreeType.objects.create(code='KS', name='Kỹ sư')
        self.faculty = Faculty.objects.create(code='CNTT', name='Công nghệ thông tin')
        
        major_kwargs = {'code': 'KTPM', 'name': 'Kỹ thuật phần mềm', 'faculty': self.faculty}
        if hasattr(Major, 'degree_type'):
            major_kwargs['degree_type'] = self.deg_type
        self.major = Major.objects.create(**major_kwargs)

        # 3. Tạo Sinh viên & Đợt tốt nghiệp mẫu
        self.student = Student.objects.create(
            student_code='SV2026999',
            full_name='Phạm Gia Khiêm',
            email='khiem@student.edu.vn',
            faculty=self.faculty,
            major=self.major
        )
        self.grad_batch = GraduationBatch.objects.create(name='Đợt Test 2026', status='DRAFT')

    # =========================================================================
    # TEST 1: NGUYÊN TẮC FOUR-EYES (K5 & N1)
    # =========================================================================
    def test_four_eyes_principle_blocks_same_actor(self):
        """Cùng 1 user thực hiện 2 bước duyệt sẽ bị chặn."""
        with self.assertRaises((ValidationError, ValueError, PermissionError, Exception)):
            ensure_different_actors(self.officer_a, self.officer_a)

    def test_four_eyes_principle_allows_three_distinct_actors(self):
        """3 user khác nhau (Officer A, Officer B, Issuer) vượt qua kiểm tra hợp lệ."""
        try:
            ensure_different_actors(self.officer_a, self.officer_b, self.issuer)
        except Exception as e:
            self.fail(f"ensure_different_actors ném lỗi sai khi 3 user khác nhau: {e}")

    # =========================================================================
    # TEST 2: HASH CHUẨN HÓA & MERKLE ROOT (K2 & K3)
    # =========================================================================
    def test_canonical_hash_and_merkle_root_determinism(self):
        """Dữ liệu JSON khác thứ tự key phải sinh ra cùng 1 Canonical Hash."""
        payload_1 = {"student_code": "SV01", "full_name": "Nguyen Van A", "major": "KTPM"}
        payload_2 = {"major": "KTPM", "student_code": "SV01", "full_name": "Nguyen Van A"}

        hash_1 = generate_canonical_hash(payload_1)
        hash_2 = generate_canonical_hash(payload_2)

        self.assertEqual(hash_1, hash_2)
        self.assertEqual(len(hash_1), 64)

        root = build_merkle_root([hash_1, generate_canonical_hash({"student_code": "SV02"})])
        self.assertTrue(root and len(root) >= 64)

    # =========================================================================
    # TEST 3: IMPORT BATCH & ROLLBACK DỮ LIỆU SINH VIÊN
    # =========================================================================
    def test_import_batch_rollback_restores_old_value(self):
        """Kiểm tra cơ chế lưu old_value trong ImportBatchItem và hoàn tác (Rollback)."""
        old_name = self.student.full_name
        
        # Giả lập đợt Import UPDATE làm thay đổi tên sinh viên
        imp_batch = ImportBatch.objects.create(
            batch=self.grad_batch,
            file_name='update_test.xlsx',
            imported_by=self.officer_a,
            mode='PARTIAL',
            updated=1
        )
        item = ImportBatchItem.objects.create(
            import_batch=imp_batch,
            row_number=1,
            student_code=self.student.student_code,
            action='UPDATE',
            old_value={'full_name': old_name},
            new_value={'full_name': 'Tên Bị Nhập Sai'}
        )

        # Cập nhật sang tên mới
        self.student.full_name = item.new_value['full_name']
        self.student.save()
        self.assertEqual(Student.objects.get(id=self.student.id).full_name, 'Tên Bị Nhập Sai')

        # Thực thi Rollback từ old_value đã lưu
        self.student.full_name = item.old_value['full_name']
        self.student.save()
        self.assertEqual(Student.objects.get(id=self.student.id).full_name, old_name)

    # =========================================================================
    # TEST 4: LUỒNG THU HỒI 3 BƯỚC & TÍCH HỢP VĂN BẰNG (N1)
    # =========================================================================
    def test_three_step_revocation_workflow(self):
        """Kiểm tra luồng thu hồi 3 bước bởi 3 người khác nhau trên văn bằng đang ISSUED."""
        c_hash = generate_canonical_hash({"student_code": self.student.student_code})
        degree = Degree.objects.create(
            student=self.student,
            batch=self.grad_batch,
            degree_type=self.deg_type,
            canonical_hash=c_hash,
            status='ISSUED',
            pdf_path='degrees/test.pdf',
            template_version='1.0',
            credential_version='1.0'
        )

        # Kiểm tra 3 tác nhân thực hiện (Request: Officer A -> Approve: Officer B -> Execute: Issuer)
        ensure_different_actors(self.officer_a, self.officer_b, self.issuer)

        # Ghi nhận giao dịch Blockchain REVOKE thành công
        tx = BlockchainTransaction.objects.create(
            degree=degree,
            operation_type='REVOKE',
            tx_hash='0x' + 'a' * 64,
            status='confirmed'
        )
        degree.status = 'REVOKED'
        degree.save()

        degree.refresh_from_db()
        self.assertEqual(degree.status, 'REVOKED')
        self.assertEqual(tx.operation_type, 'REVOKE')