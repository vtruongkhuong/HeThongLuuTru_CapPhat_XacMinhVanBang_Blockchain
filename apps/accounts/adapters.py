from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
try:
    from allauth.core.exceptions import ImmediateHttpResponse
except ImportError:
    from allauth.exceptions import ImmediateHttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    [N4] Adapter xử lý đăng nhập Google OAuth:
    - Khi sinh viên đăng nhập bằng Gmail:
      + Truy vấn bảng Student theo email.
      + Nếu có trong danh sách -> Tự động liên kết student.user = request.user và chuyển thẳng vào Student Portal.
      + Nếu không có trong danh sách -> Thông báo 'Email này chưa có hồ sơ sinh viên trong hệ thống' và chặn đăng nhập.
    """

    def pre_social_login(self, request, sociallogin):
        # 1. Trích xuất email từ tài khoản Google
        email = None
        if sociallogin.account and sociallogin.account.extra_data:
            email = sociallogin.account.extra_data.get('email')
        if not email and sociallogin.user:
            email = getattr(sociallogin.user, 'email', None)

        if not email:
            messages.error(request, "Không thể lấy thông tin email từ tài khoản Google của bạn.")
            raise ImmediateHttpResponse(redirect('accounts:login'))

        clean_email = email.strip().lower()

        # 2. Truy vấn hồ sơ sinh viên trong cơ sở dữ liệu
        from apps.students.models import Student
        student = Student.objects.filter(email__iexact=clean_email).first()

        if not student:
            messages.error(request, "Email này chưa có hồ sơ sinh viên trong hệ thống.")
            raise ImmediateHttpResponse(redirect('accounts:login'))

        # 3. Tự động liên kết nếu user đã tồn tại
        if not sociallogin.is_existing:
            existing_user = student.user
            if not existing_user:
                existing_user = User.objects.filter(email__iexact=clean_email).first()

            if existing_user:
                sociallogin.connect(request, existing_user)
                if student.user != existing_user:
                    student.user = existing_user
                    student.save(update_fields=['user'])

    def save_user(self, request, sociallogin, form=None):
        """Khi tạo user mới từ Google login, tự động gán student profile & role sinh viên"""
        user = super().save_user(request, sociallogin, form=form)
        email = (user.email or '').strip().lower()

        from apps.students.models import Student
        from apps.accounts.models import Role

        student = Student.objects.filter(email__iexact=email).first()
        if student:
            # Gỡ user khỏi các student khác nếu có
            Student.objects.filter(user=user).exclude(pk=student.pk).update(user=None)
            student.user = user
            student.save(update_fields=['user'])

        # Gán role student cho user nếu có
        student_role = Role.objects.filter(code='student').first()
        if student_role and not user.roles.filter(code='student').exists():
            user.roles.add(student_role)

        return user

    def get_login_redirect_url(self, request):
        return reverse('student_portal:dashboard')

    def get_connect_redirect_url(self, request, socialaccount):
        return reverse('student_portal:dashboard')


class CustomAccountAdapter(DefaultAccountAdapter):
    """Điều hướng thông minh sau khi đăng nhập: sinh viên vào thẳng Student Portal"""

    def get_login_redirect_url(self, request):
        user = request.user
        if hasattr(user, 'student_profile') and user.student_profile:
            return reverse('student_portal:dashboard')
        if hasattr(user, 'roles') and user.roles.filter(code='student').exists():
            return reverse('student_portal:dashboard')
        if user.is_staff or (hasattr(user, 'roles') and user.roles.filter(code__in=['issuer', 'super_admin']).exists()):
            return reverse('admin:index')
        return reverse('student_portal:dashboard')
