import uuid
from django.db import models
from django.conf import settings

class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name='audit_logs',
        help_text="Người thực hiện hành động"
    )
    action = models.CharField(max_length=255, help_text="Hành động (VD: DUYET_CAP_BANG, THU_HOI)")
    entity_type = models.CharField(max_length=255, help_text="Bảng bị tác động (VD: Student, Degree)")
    entity_id = models.CharField(max_length=255, help_text="ID của bản ghi bị tác động")
    
    old_value = models.JSONField(null=True, blank=True, help_text="Dữ liệu trước khi sửa")
    new_value = models.JSONField(null=True, blank=True, help_text="Dữ liệu sau khi sửa")
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    request_id = models.CharField(max_length=255, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_log'
        ordering = ['-timestamp']
        verbose_name = "Lịch sử hệ thống"
        verbose_name_plural = "Lịch sử hệ thống"

    def __str__(self):
        return f"{self.actor} - {self.action} - {self.entity_type} ({self.timestamp})"