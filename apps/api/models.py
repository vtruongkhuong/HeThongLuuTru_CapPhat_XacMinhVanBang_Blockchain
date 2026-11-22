import secrets
from django.db import models


class APIClient(models.Model):
    """Model đại diện cho doanh nghiệp sử dụng REST API."""
    name = models.CharField(max_length=200, verbose_name="Tên doanh nghiệp")
    api_key = models.CharField(max_length=64, unique=True, verbose_name="API Key")
    is_active = models.BooleanField(default=True, verbose_name="Đang hoạt động")
    quota_per_day = models.IntegerField(default=100, verbose_name="Giới hạn / ngày")
    usage_today = models.IntegerField(default=0, verbose_name="Đã dùng hôm nay")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")
    contact_email = models.EmailField(blank=True, verbose_name="Email liên hệ")
    
    @property
    def is_authenticated(self):
        return True
    
    class Meta:
        verbose_name = "API Client"
        verbose_name_plural = "API Clients"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({'Active' if self.is_active else 'Inactive'})"

    @classmethod
    def generate_key(cls):
        return secrets.token_hex(32)
    
    