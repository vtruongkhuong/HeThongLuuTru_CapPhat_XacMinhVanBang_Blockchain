"""
Student: hồ sơ sinh viên, dữ liệu gốc để tạo văn bằng.
Kèm theo logic quản lý Import Batch theo nguyên tắc Rollback (hoàn tác).
"""
from django.db import models
from django.conf import settings

from apps.core.models import BaseModel
from apps.academic.models import Faculty, Major


class Student(BaseModel):
    """Hồ sơ sinh viên. student_code là mã tra cứu duy nhất (mã số sinh viên)."""

    GENDER_CHOICES = [
        ('M', 'Nam'),
        ('F', 'Nữ'),
        ('O', 'Khác'),
    ]

    # Liên kết với tài khoản đăng nhập (để sinh viên login vào Student Portal)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='student_profile')
    
    student_code = models.CharField(max_length=20, unique=True, db_index=True)
    full_name = models.CharField(max_length=255)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)

    national_id = models.CharField(
        max_length=20, blank=True,
        help_text="Số CCCD/CMND, dùng để đối chiếu khi cấp văn bằng."
    )
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)

    faculty = models.ForeignKey(Faculty, on_delete=models.PROTECT, related_name='students')
    major = models.ForeignKey(Major, on_delete=models.PROTECT, related_name='students')

    enrollment_year = models.PositiveIntegerField(help_text="Năm nhập học, vd: 2020", null=True, blank=True)

    class Meta:
        db_table = 'students_student'
        ordering = ['student_code']
        indexes = [
            models.Index(fields=['student_code']),
            models.Index(fields=['national_id']),
        ]

    def __str__(self):
        return f"{self.student_code} - {self.full_name}"


class ImportBatch(BaseModel):
    """Lịch sử import theo đợt, hỗ trợ rollback theo yêu cầu của GV."""
    MODE_CHOICES = [
        ('ATOMIC', 'Atomic'),
        ('PARTIAL', 'Partial'),
    ]
    batch = models.ForeignKey('graduation.GraduationBatch', on_delete=models.CASCADE, related_name='imports')
    file_name = models.CharField(max_length=255)
    imported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES)
    
    inserted = models.IntegerField(default=0)
    updated = models.IntegerField(default=0)
    skipped = models.IntegerField(default=0)
    errors = models.IntegerField(default=0)

    class Meta:
        db_table = 'students_import_batch'
        ordering = ['-created_at']

    def __str__(self):
        return f"Import {self.file_name} - {self.batch.name}"


class ImportBatchItem(BaseModel):
    """Chi tiết từng dòng được import, lưu giá trị cũ (old_value) để phục hồi."""
    ACTION_CHOICES = [
        ('INSERT', 'Insert'),
        ('UPDATE', 'Update'),
        ('SKIP', 'Skip'),
        ('ERROR', 'Error'),
    ]
    import_batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name='items')
    row_number = models.IntegerField()
    student_code = models.CharField(max_length=20)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    
    # Lưu dưới dạng JSON để linh hoạt
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    error_message = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'students_import_batch_item'
        ordering = ['row_number']

    def __str__(self):
        return f"Row {self.row_number}: {self.student_code} - {self.action}"