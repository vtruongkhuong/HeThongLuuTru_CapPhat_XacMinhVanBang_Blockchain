"""
RBAC: User, Role, Permission, UserRole (M2M through), RolePermission (M2M through).

Thiết kế: 1 User có thể có nhiều Role (vd: vừa là 'Cán bộ đào tạo' vừa là
'Người duyệt cấp khoa'). 1 Role có nhiều Permission. Quyền hạn kiểm tra qua
apps.core.permissions.has_permission().
"""
from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import TimeStampedModel


class User(AbstractUser):
    """
    Custom User — mở rộng AbstractUser thay vì dùng default, để thêm field
    riêng cho nghiệp vụ (mã cán bộ, số điện thoại, đơn vị công tác...).
    """

    employee_code = models.CharField(
        max_length=32, unique=True, null=True, blank=True,
        help_text="Mã cán bộ/giảng viên, để trống nếu là tài khoản hệ thống."
    )
    phone_number = models.CharField(max_length=20, blank=True)
    department = models.CharField(max_length=255, blank=True)
    is_locked = models.BooleanField(
        default=False,
        help_text="Khóa tài khoản thủ công (khác với is_active của Django)."
    )

    roles = models.ManyToManyField(
        'accounts.Role',
        through='accounts.UserRole',
        through_fields=('user', 'role'),
        related_name='users',
        blank=True,
    )

    class Meta:
        db_table = 'accounts_user'

    def __str__(self):
        return self.get_full_name() or self.username


class Role(TimeStampedModel):
    """
    Vai trò trong hệ thống, ví dụ:
    - admin: quản trị toàn hệ thống
    - academic_staff: cán bộ đào tạo (nhập liệu, tạo batch)
    - reviewer: người thẩm định hồ sơ
    - approver: người duyệt phát hành (four-eyes với reviewer)
    - issuer: người ký/gửi giao dịch blockchain
    """

    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    permissions = models.ManyToManyField(
        'accounts.Permission',
        through='accounts.RolePermission',
        related_name='roles',
        blank=True,
    )

    class Meta:
        db_table = 'accounts_role'
        ordering = ['name']

    def __str__(self):
        return self.name


class Permission(TimeStampedModel):
    """
    Quyền hạn cụ thể, dạng '<resource>.<action>'.
    Ví dụ: 'student.import', 'degree.approve', 'degree.issue',
           'revocation.approve', 'blockchain.retry'
    """

    code = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'accounts_permission'
        ordering = ['code']

    def __str__(self):
        return self.code


class UserRole(TimeStampedModel):
    """Bảng trung gian User <-> Role, có thêm thông tin ai gán, khi nào."""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    assigned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_user_roles',
    )

    class Meta:
        db_table = 'accounts_user_role'
        unique_together = ('user', 'role')

    def __str__(self):
        return f"{self.user} - {self.role}"


class RolePermission(TimeStampedModel):
    """Bảng trung gian Role <-> Permission."""

    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

    class Meta:
        db_table = 'accounts_role_permission'
        unique_together = ('role', 'permission')

    def __str__(self):
        return f"{self.role} - {self.permission}"
