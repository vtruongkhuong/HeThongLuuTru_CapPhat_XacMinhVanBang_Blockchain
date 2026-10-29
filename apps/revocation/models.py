from django.db import models
from django.conf import settings


class ReasonCode(models.Model):
    code = models.CharField(max_length=50, primary_key=True, verbose_name="Mã lý do")
    description = models.CharField(max_length=255, verbose_name="Mô tả lý do thu hồi")
    
    class Meta:
        verbose_name = "Lý do thu hồi"
        verbose_name_plural = "Danh mục Lý do thu hồi"
        
    def __str__(self):
        return f"{self.code} - {self.description}"
    
    

class RevocationRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Chờ duyệt (Pending)'),
        ('APPROVED', 'Đã duyệt (Approved)'),
        ('REJECTED', 'Từ chối (Rejected)'),
        ('EXECUTED', 'Đã thực thi (Executed)'),
    ]

    degree = models.ForeignKey(
        'degrees.Degree',
        on_delete=models.CASCADE,
        related_name='revocation_requests',
        verbose_name='Văn bằng cần thu hồi'
    )
    reason_code = models.ForeignKey(
        ReasonCode,
        on_delete=models.PROTECT,
        verbose_name='Mã lý do'
    )
    description = models.TextField(null=True, blank=True, verbose_name='Mô tả chi tiết')

    # Lưu văn bằng mới thay thế (nếu thu hồi để cấp lại)
    supersedes = models.ForeignKey(
        'degrees.Degree',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='superseded_revocation_requests',
        verbose_name='Văn bằng cấp lại (Thay thế)'
    )
    tx_hash = models.CharField(max_length=100, null=True, blank=True, verbose_name='Mã giao dịch (TxHash)')

    # Workflow 3 bước (3 người khác nhau)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='requested_revocations',
        verbose_name='Người yêu cầu (Officer A)'
    )
    requested_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian yêu cầu")

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_revocations',
        verbose_name='Người duyệt (Officer B)'
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="Thời gian phê duyệt")

    executed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='executed_revocations',
        verbose_name='Người thực thi (Issuer)'
    )
    executed_at = models.DateTimeField(null=True, blank=True, verbose_name="Thời gian thực thi")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name='Trạng thái')
    
    class Meta:
        verbose_name = "Yêu cầu thu hồi"
        verbose_name_plural = "Danh sách Yêu cầu thu hồi"
        
    def __str__(self):
        return f"Thu hồi #{self.pk} - {self.degree} ({self.status})"
    
    