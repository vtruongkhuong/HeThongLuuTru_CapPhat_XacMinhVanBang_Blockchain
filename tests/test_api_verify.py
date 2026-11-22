import uuid
from datetime import date
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.academic.models import Faculty, Major, DegreeType
from apps.graduation.models import GraduationBatch
from apps.students.models import Student
from apps.degrees.models import Degree
from apps.api.models import APIClient as APIClientModel


class VerifyAPITest(TestCase):
    """Bộ kiểm thử toàn diện cho REST API Xác minh Văn bằng (Task 14)."""

    def setUp(self):
        self.client = APIClient()
        self.api_key = "test_api_key_valid_64_characters_hex_string_for_testing_00000001"
        self.api_client_obj = APIClientModel.objects.create(
            name="Doanh Nghiệp Test",
            api_key=self.api_key,
            is_active=True,
            quota_per_day=100,
            usage_today=0,
            contact_email="test@doanhnghiep.vn",
        )

        # 1. Tạo khoa, ngành, loại văn bằng
        self.faculty = Faculty.objects.create(code="CNTT", name="Khoa CNTT")
        self.degree_type = DegreeType.objects.create(
            code="KS", name="Bằng Kỹ sư", level="Đại học", is_active=True
        )
        self.major = Major.objects.create(
            code="7480103", name="Kỹ thuật phần mềm",
            faculty=self.faculty, degree_type=self.degree_type, is_active=True
        )

        # 2. Tạo đợt tốt nghiệp
        self.batch = GraduationBatch.objects.create(
            name="Đợt 1 - 2026",
            decision_no="2026/QĐ",
            decision_date=date(2026, 6, 30),
            status="CONFIRMED"
        )

        # 3. Tạo sinh viên 1 (hợp lệ) & sinh viên 2 (bị thu hồi)
        self.student_valid = Student.objects.create(
            student_code="SV_TEST_01",
            full_name="Nguyễn Văn Test",
            email="sv_test_01@student.edu.vn",
            faculty=self.faculty,
            major=self.major,
            status="active"
        )
        self.student_revoked = Student.objects.create(
            student_code="SV_TEST_02",
            full_name="Trần Thị Thu Hồi",
            email="sv_test_02@student.edu.vn",
            faculty=self.faculty,
            major=self.major,
            status="active"
        )

        # 4. Tạo văn bằng 1 (ISSUED)
        self.valid_uuid = uuid.uuid4()
        self.valid_hash = "1111111111111111111111111111111111111111111111111111111111111111"
        self.degree_valid = Degree.objects.create(
            student=self.student_valid,
            batch=self.batch,
            degree_type=self.degree_type,
            credential_public_id=self.valid_uuid,
            canonical_hash=self.valid_hash,
            status="ISSUED",
            classification="Giỏi",
            issue_date=date(2026, 7, 1),
            generated_at=timezone.now(),
        )

        # 5. Tạo văn bằng 2 (REVOKED)
        self.revoked_uuid = uuid.uuid4()
        self.revoked_hash = "2222222222222222222222222222222222222222222222222222222222222222"
        self.degree_revoked = Degree.objects.create(
            student=self.student_revoked,
            batch=self.batch,
            degree_type=self.degree_type,
            credential_public_id=self.revoked_uuid,
            canonical_hash=self.revoked_hash,
            status="REVOKED",
            classification="Khá",
            issue_date=date(2026, 7, 1),
            generated_at=timezone.now(),
        )

    def test_verify_valid_uuid(self):
        """GET /api/v1/verify/<uuid>/ với UUID hợp lệ trả về status=VERIFIED (200 OK)."""
        response = self.client.get(
            f"/api/v1/verify/{self.valid_uuid}/",
            HTTP_X_API_KEY=self.api_key
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "VERIFIED")
        self.assertEqual(response.data["student_name"], "Nguyễn Văn Test")
        self.assertFalse(response.data["is_revoked"])

    def test_verify_revoked_uuid(self):
        """GET /api/v1/verify/<uuid>/ với văn bằng bị thu hồi trả về status=REVOKED."""
        response = self.client.get(
            f"/api/v1/verify/{self.revoked_uuid}/",
            HTTP_X_API_KEY=self.api_key
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "REVOKED")
        self.assertTrue(response.data["is_revoked"])

    def test_verify_invalid_uuid(self):
        """GET /api/v1/verify/<uuid>/ với UUID không tồn tại trả về 404 NOT FOUND."""
        random_uuid = uuid.uuid4()
        response = self.client.get(
            f"/api/v1/verify/{random_uuid}/",
            HTTP_X_API_KEY=self.api_key
        )
        self.assertEqual(response.status_code, 404)

    def test_verify_no_api_key(self):
        """Gọi API mà không truyền header X-API-Key trả về lỗi 401 hoặc 403."""
        response = self.client.get(f"/api/v1/verify/{self.valid_uuid}/")
        self.assertIn(response.status_code, [401, 403])

    def test_verify_wrong_api_key(self):
        """Gọi API với API Key sai trả về lỗi 401."""
        response = self.client.get(
            f"/api/v1/verify/{self.valid_uuid}/",
            HTTP_X_API_KEY="wrong_invalid_key"
        )
        self.assertEqual(response.status_code, 401)

    def test_verify_by_hash(self):
        """POST /api/v1/verify/hash/ tìm kiếm theo canonical hash trả về 200 VERIFIED."""
        response = self.client.post(
            "/api/v1/verify/hash/",
            data={"hash": self.valid_hash},
            format="json",
            HTTP_X_API_KEY=self.api_key
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "VERIFIED")
        self.assertEqual(response.data["student_code"], "SV_TEST_01")

    def test_verify_batch(self):
        """POST /api/v1/verify/batch/ xác minh hàng loạt trả về summary chính xác."""
        uuids = [str(self.valid_uuid), str(self.revoked_uuid), str(uuid.uuid4())]
        response = self.client.post(
            "/api/v1/verify/batch/",
            data={"uuids": uuids},
            format="json",
            HTTP_X_API_KEY=self.api_key
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["summary"]["total"], 3)
        self.assertEqual(response.data["summary"]["verified"], 1)
        self.assertEqual(response.data["summary"]["revoked"], 1)
        self.assertEqual(response.data["summary"]["not_found"], 1)

    def test_download_verifiable_credential(self):
        """GET /api/v1/degrees/<uuid>/credential.json tải file chuẩn W3C VC JSON."""
        response = self.client.get(f"/api/v1/degrees/{self.valid_uuid}/credential.json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/json", response["Content-Type"])
        data = response.json()
        self.assertIn("@context", data)
        self.assertIn("VerifiableCredential", data["type"])
        self.assertEqual(data["credentialSubject"]["name"], "Nguyễn Văn Test")
        self.assertEqual(data["proof"]["canonicalHash"], self.valid_hash)

    def test_ipfs_upload(self):
        """POST /api/v1/degrees/<uuid>/ipfs-upload/ sinh CID IPFS và lưu vào Degree."""
        response = self.client.post(
            f"/api/v1/degrees/{self.valid_uuid}/ipfs-upload/",
            HTTP_X_API_KEY=self.api_key
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["cid"].startswith("Qm"))
        self.degree_valid.refresh_from_db()
        self.assertEqual(self.degree_valid.ipfs_cid, response.data["cid"])
