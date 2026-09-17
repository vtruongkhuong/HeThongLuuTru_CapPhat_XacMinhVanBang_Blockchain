"""
Helper permission dùng chung — kiểm tra quyền dựa trên RBAC custom
(apps.accounts.models: Role, Permission, UserRole, RolePermission),
KHÔNG dùng Django's default permission system.
"""
from functools import wraps

from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required


def has_permission(user, permission_code: str) -> bool:
    """
    Kiểm tra user có quyền `permission_code` hay không, thông qua Role được gán.

    Ví dụ permission_code: 'degree.approve', 'degree.issue', 'student.import'
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True

    return user.roles.filter(
        rolepermission__permission__code=permission_code
    ).exists()


def permission_required(permission_code: str):
    """
    Decorator cho view-based: @permission_required('degree.approve')
    Dùng cho function-based view (khác với Django's built-in decorator
    vì hệ thống quyền ở đây là custom RBAC).
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if not has_permission(request.user, permission_code):
                raise PermissionDenied(
                    f"Bạn không có quyền '{permission_code}' để thực hiện thao tác này."
                )
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


class PermissionRequiredMixin:
    """Mixin cho class-based view. Set `permission_code = 'xxx.yyy'` trên view con."""

    permission_code = None

    def dispatch(self, request, *args, **kwargs):
        if self.permission_code and not has_permission(request.user, self.permission_code):
            raise PermissionDenied(
                f"Bạn không có quyền '{self.permission_code}' để thực hiện thao tác này."
            )
        return super().dispatch(request, *args, **kwargs)


class FourEyesRequired:
    """
    Nguyên tắc 'four-eyes': người duyệt (approve) không được là người tạo/submit.
    Dùng trong apps.workflow.services khi chuyển trạng thái Reviewed -> Approved.
    """

    @staticmethod
    def check(created_by, actor):
        if created_by and actor and created_by.pk == actor.pk:
            raise PermissionDenied(
                "Người duyệt không được trùng với người tạo/nộp hồ sơ (four-eyes principle)."
            )
