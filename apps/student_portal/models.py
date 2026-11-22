import uuid
from datetime import timedelta
from django.db import models
from django.utils import timezone
from apps.students.models import Student


class StudentProfileShareLink(models.Model):
    """
    [Nghĩa - Task 3] Link chia sẻ hồ sơ văn bằng tạm thời dành cho nhà tuyển dụng (7-30 ngày).
    Sinh viên có thể đính kèm link này vào CV xin việc để nhà tuyển dụng xem và đối soát trực tiếp.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='share_links', verbose_name="Sinh viên")
    token = models.CharField(max_length=64, unique=True, db_index=True, verbose_name="Mã token chia sẻ")
    label = models.CharField(max_length=255, blank=True, null=True, verbose_name="Mục đích / Nhà tuyển dụng")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời điểm tạo")
    expires_at = models.DateTimeField(verbose_name="Thời điểm hết hạn")
    days_valid = models.IntegerField(default=14, verbose_name="Số ngày hiệu lực")
    view_count = models.PositiveIntegerField(default=0, verbose_name="Số lượt xem")
    max_views = models.PositiveIntegerField(default=0, verbose_name="Số lượt xem tối đa (0 = không giới hạn)")
    password_hash = models.CharField(max_length=128, blank=True, default="", verbose_name="Mật khẩu bảo vệ (hash)")
    viewer_log = models.JSONField(default=list, blank=True, verbose_name="Nhật ký người xem")
    is_active = models.BooleanField(default=True, verbose_name="Đang kích hoạt")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Link chia sẻ hồ sơ"
        verbose_name_plural = "Danh sách link chia sẻ hồ sơ"

    def __str__(self):
        return f"{self.student.student_code} - {self.token} (Hạn: {self.expires_at.strftime('%d/%m/%Y')})"

    @property
    def has_password(self):
        return bool(self.password_hash and self.password_hash.strip())

    @property
    def is_view_limit_reached(self):
        return self.max_views > 0 and self.view_count >= self.max_views

    @property
    def is_expired(self):
        return (not self.is_active) or (timezone.now() > self.expires_at)

    @property
    def is_accessible(self):
        return (not self.is_expired) and (not self.is_view_limit_reached)

    @property
    def remaining_days(self):
        if self.is_expired:
            return 0
        delta = self.expires_at - timezone.now()
        return max(0, delta.days + (1 if delta.seconds > 0 else 0))
