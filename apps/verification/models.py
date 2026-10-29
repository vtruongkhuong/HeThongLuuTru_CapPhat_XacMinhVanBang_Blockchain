from django.db import models
from apps.degrees.models import Degree

class VerificationLog(models.Model):
    search_query = models.CharField(max_length=255, verbose_name="Mã tra cứu")
    degree = models.ForeignKey(Degree, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Văn bằng liên quan")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="Địa chỉ IP")
    user_agent = models.TextField(null=True, blank=True, verbose_name="Trình duyệt/Thiết bị")
    is_successful = models.BooleanField(default=False, verbose_name="Trạng thái tra cứu")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian tra cứu")
    
    RESULT_CHOICES = [
        ('VALID', 'Hợp lệ'),
        ('NOT_FOUND', 'Không tìm thấy'),
        ('REVOKED', 'Đã thu hồi'),
        ('TAMPERED', 'Bị giả mạo'),
    ]
    
    result_status = models.CharField(max_length=50, default='VALID', null=True, blank=True, verbose_name="Kết quả tra cứu")
    
    TYPE_CHOICES = [
        ('PUBLIC_SEARCH', 'Tra cứu trực tuyến'),
        ('PDF', 'Quét file PDF'),
        ('CODE', 'Tra cứu mã bằng'),
    ]
    
    verification_type = models.CharField(max_length=50, default='PUBLIC_SEARCH', null=True, blank=True,  verbose_name="Hình thức xác minh")
    

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Lịch sử tra cứu"
        verbose_name_plural = "Lịch sử tra cứu"

    def __str__(self):
        return f"{self.search_query} - {self.created_at.strftime('%d/%m/%Y %H:%M')}"