import uuid
from django.db import models
from django.conf import settings

class Degree(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('GENERATED', 'Generated'),
        ('REVIEWED', 'Reviewed'),
        ('APPROVED', 'Approved'),
        ('ISSUANCE_PENDING', 'Issuance Pending'),
        ('ISSUED', 'Issued'),
        ('REVOKED', 'Revoked'),
    ]

    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='degrees')
    batch = models.ForeignKey('graduation.GraduationBatch', on_delete=models.CASCADE, related_name='degrees')
    degree_type = models.ForeignKey('academic.DegreeType', on_delete=models.PROTECT)
    
    # Chuẩn hóa ULID/UUID 36 ký tự theo ERD mới
    credential_public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    classification = models.CharField(max_length=50, null=True, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    pdf_path = models.CharField(max_length=255)
    template_version = models.CharField(max_length=20)
    credential_version = models.CharField(max_length=20)
    generated_at = models.DateTimeField(null=True, blank=True)
    
    # Hash chuẩn hóa để ghi lên chain
    canonical_hash = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    
    # Tracking Four-eyes principle
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_degrees')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_degrees')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Versioning
    supersedes = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='superseded_by')

    def __str__(self):
        return f"{self.credential_public_id} - {self.student.full_name}"