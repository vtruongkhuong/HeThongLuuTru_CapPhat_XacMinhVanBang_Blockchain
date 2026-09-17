"""
Base model / mixin dùng chung cho toàn bộ app nghiệp vụ.

- TimeStampedModel: tự động có created_at, updated_at.
- SoftDeleteMixin: xóa mềm (is_deleted) thay vì xóa thật, kèm manager lọc sẵn.
"""
from django.db import models


class TimeStampedModel(models.Model):
    """Abstract model: mọi bảng nghiệp vụ nên kế thừa để có timestamp chuẩn."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ActiveManager(models.Manager):
    """Manager mặc định: chỉ trả về bản ghi chưa bị xóa mềm."""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class SoftDeleteMixin(models.Model):
    """
    Abstract model cho xóa mềm.

    Dùng khi bản ghi không nên bị xóa thật (vd: Student, Degree) vì có thể
    liên quan tới lịch sử / audit / blockchain đã ghi nhận.
    """

    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = ActiveManager()       # chỉ lấy bản ghi active
    all_objects = models.Manager()  # lấy tất cả kể cả đã xóa

    class Meta:
        abstract = True

    def soft_delete(self):
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=['is_deleted', 'deleted_at'])


class BaseModel(TimeStampedModel, SoftDeleteMixin):
    """Kết hợp cả 2 mixin trên — dùng cho hầu hết model nghiệp vụ chính."""

    class Meta:
        abstract = True
