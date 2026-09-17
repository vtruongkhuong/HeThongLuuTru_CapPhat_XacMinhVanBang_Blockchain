from django.db import models
from django.conf import settings

class GraduationBatch(models.Model):
    # Các trạng thái của quy trình 4-eyes
    STATUS_CHOICES = (
        ('DRAFT', 'Bản nháp'),
        ('PENDING', 'Chờ duyệt'),
        ('APPROVED', 'Đã duyệt'),
        ('REJECTED', 'Từ chối'),
    )

    name = models.CharField(max_length=150, verbose_name="Tên đợt tốt nghiệp")
    decision_no = models.CharField(max_length=50, null=True, blank=True, verbose_name="Số quyết định")
    decision_date = models.DateField(null=True, blank=True, verbose_name="Ngày quyết định")
    
    # 1. Trạng thái kiểm duyệt
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='DRAFT',
        verbose_name="Trạng thái"
    )
    
    # 2. Dấu vết 4-eyes (Maker & Checker)
    maker = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='made_graduation_batches',
        verbose_name="Người lập (Maker)"
    )
    checker = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='checked_graduation_batches',
        verbose_name="Người duyệt (Checker)"
    )
    
    # 3. Thời gian và Ghi chú (Lý do từ chối)
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="Thời gian duyệt")
    rejection_reason = models.TextField(null=True, blank=True, verbose_name="Lý do từ chối")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Đợt tốt nghiệp"
        verbose_name_plural = "Các đợt tốt nghiệp"
        
    # Thông tin Blockchain
    merkle_root = models.CharField(max_length=64, null=True, blank=True, verbose_name="Mã Merkle Root")
    tx_hash = models.CharField(max_length=100, null=True, blank=True, verbose_name="Mã giao dịch Blockchain")