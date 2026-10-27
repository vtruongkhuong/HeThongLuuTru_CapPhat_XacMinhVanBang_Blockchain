from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()


class EmailOrUsernameModelBackend(ModelBackend):
    """
    Backend xác thực linh hoạt:
    Cho phép sinh viên và cán bộ đăng nhập bằng:
      - Tên đăng nhập (username)
      - Hoặc Email / Gmail đã đăng ký trong hệ thống
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if not username or not password:
            return None

        clean_login = username.strip()

        try:
            # Tìm user theo username hoặc email (không phân biệt hoa thường)
            user = User.objects.filter(
                Q(username__iexact=clean_login) | Q(email__iexact=clean_login)
            ).first()

            if user and user.check_password(password) and self.user_can_authenticate(user):
                return user
        except Exception:
            return None

        return None
