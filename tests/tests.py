import os
import tempfile
import uuid
import pandas as pd
from unittest.mock import MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.academic.models import Faculty, Major, DegreeType
from apps.students.models import Student, ImportBatch, ImportBatchItem
from apps.students.services import process_student_import_logic, rollback_import_batch
from apps.blockchain.models import BlockchainTransaction, IssuanceBatch
from apps.blockchain.management.commands.reconcile_chain import (
    reconcile_pending_transactions,
    reconcile_merkle_roots
)
from apps.blockchain.services import build_merkle_root, get_merkle_proof, verify_merkle_proof
from apps.degrees.canonicalizer import canonical_hash, HASH_VERSION
from apps.degrees.models import Degree
from apps.graduation.models import GraduationBatch
from apps.workflow.services import ensure_different_actors, transition
from apps.audit.models import AuditLog
from apps.audit.services import log_action

User = get_user_model()


class H10SystemTestSuite(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='admin_test', email='admin@ntt.edu.vn', password='password123'
        )
        self.maker = User.objects.create_user(
            username='maker_user', email='maker@ntt.edu.vn', password='password123'
        )
        self.checker = User.objects.create_user(
            username='checker_user', email='checker@ntt.edu.vn', password='password123'
        )
        self.normal_user = User.objects.create_user(
            username='student_test', email='sv@ntt.edu.vn', password='password123'
        )
        self.faculty = Faculty.objects.create(code='CNTT', name='Khoa Công Nghệ Thông Tin')
        self.deg_type = DegreeType.objects.create(code='CN', name='Cử nhân', template_name='bachelor_degree.html')
        self.major = Major.objects.create(code='KTPM', name='Kỹ thuật phần mềm', faculty=self.faculty, degree_type=self.deg_type)
        self.grad_batch = GraduationBatch.objects.create(name='Đợt 1 - 2026', maker=self.maker, status='DRAFT')

    def test_1_student_import_and_rollback_flow(self):
        """Kiểm thử H5: Import Excel (Insert, Update, Error) và Hoàn tác (Rollback)"""
        # Tạo sẵn 1 sinh viên để test nhánh UPDATE
        Student.objects.create(
            student_code='SV001', full_name='Tên Cũ', major=self.major, faculty=self.faculty, email='sv001@student.ctuet.edu.vn'
        )

        # Tạo file Excel tạm thời với 3 dòng: 1 Update, 1 Insert mới, 1 Lỗi mã ngành
        df = pd.DataFrame([
            {'Mã SV': 'SV001', 'Họ và Tên': 'Tên Đã Cập Nhật', 'Mã Ngành': 'KTPM', 'Năm Nhập Học': '2022'},
            {'Mã SV': 'SV002', 'Họ và Tên': 'Nguyễn Văn Mới', 'Mã Ngành': 'KTPM', 'Năm Nhập Học': '2023'},
            {'Mã SV': 'SV003', 'Họ và Tên': 'Sinh Viên Lỗi', 'Mã Ngành': 'NGANH_AO', 'Năm Nhập Học': '2023'},
        ])

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            df.to_excel(tmp.name, index=False)
            tmp_path = tmp.name

        try:
            batch = ImportBatch.objects.create(
                batch=self.grad_batch,
                file_name='test.xlsx',
                imported_by=self.superuser,
                mode='PARTIAL'
            )
            success, msg = process_student_import_logic(batch.id, tmp_path)

            self.assertTrue(success)
            batch.refresh_from_db()
            self.assertEqual(batch.inserted, 1)
            self.assertEqual(batch.updated, 1)
            self.assertEqual(batch.errors, 1)
            self.assertEqual(Student.objects.count(), 2)
            self.assertEqual(Student.objects.get(student_code='SV001').full_name, 'Tên Đã Cập Nhật')

            # Thực hiện Rollback
            rollback_import_batch(batch.id)
            batch.refresh_from_db()
            self.assertEqual(batch.status, 'rolled_back')
            # SV002 mới thêm phải bị xóa, SV001 phải quay về 'Tên Cũ'
            self.assertFalse(Student.objects.filter(student_code='SV002').exists())
            self.assertEqual(Student.objects.get(student_code='SV001').full_name, 'Tên Cũ')
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_2_blockchain_reconcile_logic(self):
        """Kiểm thử H7: Đối soát giao dịch Blockchain (pending -> confirmed / failed)"""
        tx_ok = BlockchainTransaction.objects.create(tx_hash='0x111', status='pending')
        tx_fail = BlockchainTransaction.objects.create(tx_hash='0x222', status='pending')

        mock_w3 = MagicMock()
        def side_effect(tx_hash):
            if tx_hash == '0x111':
                return {'status': 1}
            return {'status': 0}

        mock_w3.eth.get_transaction_receipt.side_effect = side_effect
        result = reconcile_pending_transactions(w3=mock_w3)

        self.assertEqual(result['confirmed'], 1)
        self.assertEqual(result['failed'], 1)
        tx_ok.refresh_from_db()
        tx_fail.refresh_from_db()
        self.assertEqual(tx_ok.status, 'confirmed')
        self.assertEqual(tx_fail.status, 'failed')

    def test_3_audit_log_and_security_permissions(self):
        """Kiểm thử H8 & H9: Ghi nhận AuditLog và Chặn quyền truy cập trái phép"""
        log = log_action(
            actor=self.superuser,
            action='IMPORT_EXCEL',
            entity_type='ImportBatch',
            entity_id='999',
            new={'status': 'completed'}
        )
        self.assertEqual(AuditLog.objects.count(), 1)
        self.assertEqual(log.action, 'IMPORT_EXCEL')

        # Kiểm tra user thường không được phép truy cập trang xuất báo cáo CSV
        client = Client()
        client.force_login(self.normal_user)
        response = client.get(reverse('reporting:export_csv'))
        self.assertEqual(response.status_code, 403)

    def test_4_four_eyes_principle_flow(self):
        """Kiểm thử H10: Luồng 4 mắt (Maker không được tự duyệt)"""
        # Maker tự duyệt chính mình -> Bắt buộc ném ngoại lệ ValidationError
        with self.assertRaises(ValidationError):
            ensure_different_actors(self.maker, self.maker)

        # Hai người khác nhau -> Hợp lệ
        self.assertTrue(ensure_different_actors(self.maker, self.checker))

        student = Student.objects.create(
            student_code='SV_4EYES', full_name='Lê Văn Test', major=self.major, faculty=self.faculty, email='sv_4eyes@ctuet.edu.vn'
        )
        degree = Degree.objects.create(
            student=student,
            batch=self.grad_batch,
            degree_type=self.deg_type,
            credential_public_id=uuid.uuid4(),
            canonical_hash='0x' + 'a' * 64,
            status='REVIEWED',
            reviewed_by=self.maker
        )

        # Maker tự phê duyệt văn bằng mình đã review -> Phải bị chặn
        with self.assertRaises(ValidationError):
            transition(degree, 'APPROVED', actor=self.maker)

        # Checker khác phê duyệt -> Thành công
        updated = transition(degree, 'APPROVED', actor=self.checker)
        self.assertEqual(updated.status, 'APPROVED')
        self.assertEqual(updated.approved_by, self.checker)

    def test_5_merkle_tree_root_and_proof_generation(self):
        """Kiểm thử H10: Sinh Merkle Root và Proof thật, xác minh 100% khớp"""
        # Sinh 5 lá canonical hashes
        leaves = []
        for i in range(5):
            leaf_data = {
                "hash_version": HASH_VERSION,
                "credential_public_id": str(uuid.uuid4()),
                "student_code": f"SV00{i}",
                "full_name": f"Sinh Viên {i}",
                "major_code": "KTPM",
                "degree_type_code": "CN",
                "batch_name": "Đợt 1 - 2026",
                "classification": "Giỏi",
                "issue_date": "2026-10-29",
            }
            leaves.append(canonical_hash(leaf_data))

        # 1. Tính Merkle Root
        root = build_merkle_root(leaves)
        self.assertTrue(len(root.replace('0x', '')) == 64)

        # 2. Sinh Proof cho từng leaf và verify
        for idx, leaf in enumerate(leaves):
            proof = get_merkle_proof(leaves, idx)
            is_valid = verify_merkle_proof(leaf, proof, root)
            self.assertTrue(is_valid, f"Proof của phần tử {idx} phải hợp lệ với Merkle Root!")

    def test_6_reconcile_chain_tamper_detection(self):
        """Kiểm thử H7 & H10: Lệnh đối soát phát hiện tức thì khi Merkle Root bị sửa lén trong DB"""
        ib = IssuanceBatch.objects.create(
            graduation_batch=self.grad_batch,
            merkle_root='0x' + '9' * 64,
            chain_id='0x' + '8' * 64,
            status='CONFIRMED'
        )

        # Mock BlockchainClient trả về root thật trên chain là '0x' + '9'*64
        mock_client = MagicMock()
        mock_client.get_batch.return_value = {
            'root': '0x' + '9' * 64,
            'issued_at': 1730000000,
            'count': 10,
            'issuer': '0x123'
        }

        # Trường hợp 1: Dữ liệu DB khớp với Chain
        res_ok = reconcile_merkle_roots(client=mock_client)
        self.assertEqual(res_ok['tampered_batches'], 0)
        self.assertEqual(res_ok['valid_batches'], 1)

        # Trường hợp 2: Có kẻ cố tình sửa lén 1 ký tự mã hash trong DB
        ib.merkle_root = '0x' + '9' * 63 + '0'  # Sửa ký tự cuối thành '0'
        ib.save()

        res_tampered = reconcile_merkle_roots(client=mock_client)
        self.assertEqual(res_tampered['tampered_batches'], 1)
        self.assertEqual(res_tampered['details'][0]['status'], 'TAMPERED')
        self.assertIn('BÁO ĐỘNG GIAN LẬN', res_tampered['details'][0]['message'])

    def test_7_single_degree_form_creation(self):
        """Kiểm thử Phần 2: Form tạo văn bằng đơn lẻ trực tiếp cho Cán bộ nhập (không qua Excel)"""
        from apps.degrees.forms import SingleDegreeForm

        # 1. Thử tạo với sinh viên mới trực tiếp
        form_data_new = {
            'student_mode': 'new',
            'student_code': 'BSINGLE01',
            'full_name': 'Sinh Viên Cấp Lẻ 1',
            'email': 'single1@student.ctuet.edu.vn',
            'date_of_birth': '2003-08-15',
            'gender': 'M',
            'major': self.major.id,
            'gpa_score': 3.65,
            'batch': self.grad_batch.id,
            'degree_type': self.deg_type.id,
            'auto_submit': True
        }
        form = SingleDegreeForm(data=form_data_new)
        self.assertTrue(form.is_valid(), f"Form hợp lệ nhưng báo lỗi: {form.errors}")
        deg = form.save(self.maker)
        self.assertIsNotNone(deg.id)
        self.assertEqual(deg.student.student_code, 'BSINGLE01')
        self.assertIn(deg.classification.upper(), ['XUẤT SẮC', 'XUAT SAC'])
        self.assertEqual(deg.status, 'REVIEWED')
        self.assertTrue(len(deg.canonical_hash) == 64)

        # 2. Thử tạo với sinh viên có sẵn trong hệ thống
        existing_sv = Student.objects.create(
            student_code='BSINGLE02',
            full_name='Sinh Viên Cấp Lẻ 2',
            email='single2@student.ctuet.edu.vn',
            faculty=self.faculty,
            major=self.major,
            gpa_score=3.15,
            status='approved'
        )
        batch2 = GraduationBatch.objects.create(name='Đợt 2 - 2026', maker=self.maker, status='DRAFT')
        form_data_exist = {
            'student_mode': 'existing',
            'existing_student': existing_sv.id,
            'batch': batch2.id,
            'auto_submit': False
        }
        form2 = SingleDegreeForm(data=form_data_exist)
        self.assertTrue(form2.is_valid(), f"Form sinh viên có sẵn báo lỗi: {form2.errors}")
        deg2 = form2.save(self.maker)
        self.assertEqual(deg2.student.id, existing_sv.id)
        self.assertEqual(deg2.status, 'DRAFT')

    def test_8_so_goc_excel_and_pdf_generation(self):
        """Kiểm thử Phần 2: Xuất Sổ gốc Bộ GD&ĐT chuẩn Thông tư 21/2019/TT-BGDĐT (Excel & PDF)"""
        from apps.reporting.so_goc_service import generate_so_goc_excel, generate_so_goc_pdf

        # Tạo 1 Degree mẫu
        sv = Student.objects.create(
            student_code='BSOGOC01',
            full_name='Nguyễn Văn Sổ Gốc',
            email='sogoc@student.ctuet.edu.vn',
            faculty=self.faculty,
            major=self.major,
            gpa_score=3.45,
            status='approved'
        )
        degree = Degree.objects.create(
            student=sv,
            batch=self.grad_batch,
            degree_type=self.deg_type,
            classification='Giỏi',
            canonical_hash='a' * 64,
            status='ISSUED'
        )

        # 1. Kiểm tra xuất Excel
        excel_bytes = generate_so_goc_excel(batch=self.grad_batch)
        self.assertIsInstance(excel_bytes, bytes)
        self.assertGreater(len(excel_bytes), 1000)
        # Kiểm tra file excel đọc được bằng openpyxl
        import openpyxl
        import io
        wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
        ws = wb.active
        self.assertIn("SỔ GỐC CẤP PHÁT VĂN BẰNG", ws["A4"].value)

        # 2. Kiểm tra xuất PDF
        pdf_bytes = generate_so_goc_pdf(batch=self.grad_batch)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b'%PDF'), "Nội dung PDF phải bắt đầu bằng %PDF header")

    def test_9_congratulation_email_celery_task(self):
        """Kiểm thử Phần 2: Celery tự động gửi email chúc mừng kèm PDF & QR cho sinh viên khi duyệt On-Chain"""
        from apps.degrees.tasks import send_degree_congratulation_email
        from django.core import mail

        sv = Student.objects.create(
            student_code='BMAIL01',
            full_name='Trần Email Tân Cử Nhân',
            email='tancunhan@student.ctuet.edu.vn',
            faculty=self.faculty,
            major=self.major,
            gpa_score=3.70,
            status='approved'
        )
        degree = Degree.objects.create(
            student=sv,
            batch=self.grad_batch,
            degree_type=self.deg_type,
            classification='Xuất sắc',
            canonical_hash='b' * 64,
            status='ISSUED'
        )

        mail.outbox.clear()
        res = send_degree_congratulation_email(degree.id)
        self.assertEqual(res['status'], 'success')
        self.assertEqual(res['recipient'], 'tancunhan@student.ctuet.edu.vn')

        # Kiểm tra hòm thư Django outbox
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertIn('Chúc mừng tốt nghiệp', sent_email.subject)
        self.assertIn('tancunhan@student.ctuet.edu.vn', sent_email.to)
        # Kiểm tra có đính kèm file PDF
        has_pdf = False
        for att in sent_email.attachments:
            if isinstance(att, tuple) and att[0].endswith('.pdf'):
                has_pdf = True
            elif hasattr(att, 'get_filename') and att.get_filename() and att.get_filename().endswith('.pdf'):
                has_pdf = True
        self.assertTrue(has_pdf, "Email phải có đính kèm file văn bằng PDF!")

