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


class EmployerVerificationSession(models.Model):
    """
    [BƯỚC 1 - HR Session] Lưu phiên kiểm định hàng loạt của Doanh nghiệp / Nhà tuyển dụng.
    Lưu vết mã phiên, tên doanh nghiệp, tên đợt tuyển dụng, kết quả kiểm định chi tiết và IP.
    """
    session_code = models.CharField(max_length=50, unique=True, verbose_name="Mã phiên đối soát")  # VD: "HR-20261122-001"
    employer_name = models.CharField(max_length=200, blank=True, default="", verbose_name="Tên doanh nghiệp")
    recruitment_name = models.CharField(max_length=200, blank=True, default="", verbose_name="Tên đợt tuyển dụng") # VD: "Tuyển dụng Q4/2026"
    total_checked = models.IntegerField(default=0, verbose_name="Tổng số hồ sơ")
    total_verified = models.IntegerField(default=0, verbose_name="Hợp lệ (Chuẩn Blockchain)")
    total_tampered = models.IntegerField(default=0, verbose_name="Nghi vấn làm giả")
    total_revoked = models.IntegerField(default=0, verbose_name="Đã bị thu hồi")
    total_not_found = models.IntegerField(default=0, verbose_name="Không tìm thấy")
    result_detail = models.JSONField(default=list, blank=True, verbose_name="Chi tiết từng ứng viên")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="Địa chỉ IP")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian thực hiện")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Phiên thẩm định doanh nghiệp"
        verbose_name_plural = "Lịch sử phiên thẩm định doanh nghiệp"

    def __str__(self):
        emp = self.employer_name or "Doanh nghiệp"
        return f"{self.session_code} - {emp} ({self.total_checked} hồ sơ)"
