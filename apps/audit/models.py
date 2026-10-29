import uuid
from django.db import models
from django.conf import settings

class AuditLog(models.Model):
    # CHUẨN HOÁ CÁC HÀNH ĐỘNG THEO YÊU CẦU H8
    ACTION_CHOICES = [
        ('LOGIN', 'Đăng nhập'),
        ('IMPORT_EXCEL', 'Import Excel'),
        ('ROLLBACK', 'Hoàn tác Import'),
        ('RENDER_PDF', 'Kết xuất PDF'),
        ('APPROVE_BATCH', 'Ký duyệt đợt'),
        ('ISSUE_DEGREE', 'Ký phát hành'),
        ('REVOKE_DEGREE', 'Thu hồi văn bằng'),
        ('OTHER', 'Khác'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name="Mã nhật ký")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name='audit_logs',
        verbose_name="Người thực hiện",
        help_text="Người thực hiện hành động"
    )
    
    # SỬA LẠI: Thêm choices để giới hạn các hành động hợp lệ
    action = models.CharField(max_length=255, choices=ACTION_CHOICES, help_text="Hành động", verbose_name="Hành động")
    
    entity_type = models.CharField(max_length=255, help_text="Bảng bị tác động (VD: Student, Degree, GraduationBatch)", verbose_name="Đối tượng tác động")
    entity_id = models.CharField(max_length=255, help_text="ID của bản ghi bị tác động", verbose_name="Mã đối tượng (ID)")
    
    old_value = models.JSONField(null=True, blank=True, help_text="Dữ liệu trước khi sửa", verbose_name="Dữ liệu trước khi sửa")
    new_value = models.JSONField(null=True, blank=True, help_text="Dữ liệu sau khi sửa", verbose_name="Dữ liệu sau khi sửa")
    
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="Địa chỉ IP")
    request_id = models.CharField(max_length=255, null=True, blank=True, verbose_name="Mã Request")
    
    # THÊM MỚI: Bổ sung user_agent để giám sát chi tiết hơn
    user_agent = models.TextField(null=True, blank=True, verbose_name="Trình duyệt / Thiết bị")
    
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian")

    class Meta:
        db_table = 'audit_log'
        ordering = ['-timestamp']
        verbose_name = "Lịch sử hệ thống"
        verbose_name_plural = "Lịch sử hệ thống"

    def __str__(self):
        action_display = dict(self.ACTION_CHOICES).get(self.action, self.action)
        return f"{self.actor} - {action_display} - {self.entity_type} ({self.timestamp})"