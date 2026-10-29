import uuid
from django.db import models
from django.conf import settings

class Degree(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Bản nháp'),
        ('GENERATED', 'Đã tạo phôi PDF'),
        ('REVIEWED', 'Đã thẩm định'),
        ('APPROVED', 'Đã phê duyệt'),
        ('ISSUANCE_PENDING', 'Chờ phát hành On-Chain'),
        ('ISSUED', 'Đã phát hành On-Chain'),
        ('REVOKED', 'Đã thu hồi'),
    ]

    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='degrees', verbose_name="Sinh viên")
    batch = models.ForeignKey('graduation.GraduationBatch', on_delete=models.CASCADE, related_name='degrees', verbose_name="Đợt tốt nghiệp")
    degree_type = models.ForeignKey('academic.DegreeType', on_delete=models.PROTECT, verbose_name="Loại văn bằng")
    
    # Chuẩn hóa ULID/UUID 36 ký tự theo ERD mới
    credential_public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    classification = models.CharField(max_length=50, null=True, blank=True, verbose_name="Xếp loại tốt nghiệp")
    issue_date = models.DateField(null=True, blank=True, verbose_name="Ngày cấp bằng")
    pdf_path = models.CharField(max_length=255)

    pdf_sha256 = models.CharField(max_length=64, null=True, blank=True)

    template_version = models.CharField(max_length=20)
    credential_version = models.CharField(max_length=20)
    generated_at = models.DateTimeField(null=True, blank=True)
    
    # Hash chuẩn hóa để ghi lên chain
    canonical_hash = models.CharField(max_length=64, unique=True, verbose_name="Mã băm chuẩn hóa (Hash)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT', verbose_name="Trạng thái")
    
    # Tracking Four-eyes principle
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_degrees')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_degrees')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Versioning
    supersedes = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='superseded_by')

    def __str__(self):
        return f"{self.credential_public_id} - {self.student.full_name}"
    
        
    @property
    def graduation_year(self):
        d = self.issue_date or self.approved_at
        return d.year if d else ""

    @property
    def serial_number(self):
        return f"CTUT-{self.graduation_year or 'XXXX'}-{self.pk:06d}"
    
    class Meta:
        verbose_name = "Văn bằng số"
        verbose_name_plural = "Sổ cái Văn bằng số"