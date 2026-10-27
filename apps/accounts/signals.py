from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from allauth.account.signals import user_signed_up

User = get_user_model()


@receiver(user_logged_in)
def auto_link_student_on_login(sender, request, user, **kwargs):
    """
    [N4] Khi bất kỳ người dùng nào đăng nhập:
    Nếu email trùng với hồ sơ Student trong CSDL -> Tự động gắn kết student.user = user
    và cấp quyền vai trò sinh viên nếu chưa có.
    """
    if not user or not user.is_authenticated or not user.email:
        return

    clean_email = user.email.strip().lower()
    from apps.students.models import Student
    from apps.accounts.models import Role

    student = Student.objects.filter(email__iexact=clean_email).first()
    if student:
        if student.user != user:
            # Gỡ user khỏi các student khác để đảm bảo 1-1
            Student.objects.filter(user=user).exclude(pk=student.pk).update(user=None)
            student.user = user
            student.save(update_fields=['user'])

        student_role = Role.objects.filter(code='student').first()
        if student_role and not user.roles.filter(code='student').exists():
            user.roles.add(student_role)


@receiver(user_signed_up)
def handle_user_signed_up(request, user, **kwargs):
    """Xử lý sau khi user đăng ký mới qua Allauth / Google"""
    auto_link_student_on_login(sender=None, request=request, user=user)
