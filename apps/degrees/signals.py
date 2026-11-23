"""
Signals cho ứng dụng apps.degrees:
Tự động gửi email thông báo khi trạng thái văn bằng thay đổi sang ISSUED hoặc REVOKED.
"""
import logging
from django.db.models.signals import post_save, post_init
from django.dispatch import receiver
from .models import Degree
from .email_service import send_degree_issued_email, send_degree_revoked_email

logger = logging.getLogger(__name__)


@receiver(post_init, sender=Degree)
def track_degree_previous_status(sender, instance, **kwargs):
    """Lưu lại trạng thái ban đầu của đối tượng khi nạp từ Database"""
    instance._previous_status = instance.status


@receiver(post_save, sender=Degree)
def on_degree_status_change(sender, instance, created=False, **kwargs):
    """
    Tự động kích hoạt gửi email thông báo:
    - Khi văn bằng chuyển sang ISSUED: Gửi email chúc mừng và thông tin bằng số.
    - Khi văn bằng chuyển sang REVOKED: Gửi email cảnh báo thu hồi văn bằng.
    """
    prev_status = getattr(instance, '_previous_status', None)

    # 1. Phát hành thành công (ISSUED)
    if instance.status == 'ISSUED' and (created or prev_status != 'ISSUED'):
        student = getattr(instance, 'student', None)
        if student and getattr(student, 'email', None):
            logger.info(f"[Degree Signal] Kích hoạt gửi email ISSUED cho sinh viên {student.student_code} ({student.email})")
            send_degree_issued_email(instance)

        # In-app Notification cho SV
        if student and getattr(student, 'user', None):
            try:
                from apps.accounts.models import Notification
                degree_type_name = instance.degree_type.name if instance.degree_type else "Tốt nghiệp"
                Notification.objects.create(
                    user=student.user,
                    title="Văn bằng đã được cấp phát",
                    message=f"Văn bằng {degree_type_name} của bạn đã được cấp thành công.",
                    link="/portal/dashboard/",
                    icon="school"
                )
                logger.info(f"[Degree Signal] Đã tạo Notification ISSUED cho sinh viên {student.user.username}")
            except Exception as ne:
                logger.warning(f"[Degree Signal] Không thể tạo Notification: {ne}")

    # 2. Thu hồi văn bằng (REVOKED)
    elif instance.status == 'REVOKED' and (created or prev_status != 'REVOKED'):
        student = getattr(instance, 'student', None)
        if student and getattr(student, 'email', None):
            reason = None
            if hasattr(instance, 'revocation_requests'):
                reason = instance.revocation_requests.last()
            logger.info(f"[Degree Signal] Kích hoạt gửi email REVOKED cho sinh viên {student.student_code} ({student.email})")
            send_degree_revoked_email(instance, reason)

        # In-app Notification cho SV
        if student and getattr(student, 'user', None):
            try:
                from apps.accounts.models import Notification
                degree_type_name = instance.degree_type.name if instance.degree_type else "Tốt nghiệp"
                Notification.objects.create(
                    user=student.user,
                    title="Văn bằng đã bị thu hồi",
                    message=f"Văn bằng {degree_type_name} của bạn đã bị thu hồi trên hệ thống.",
                    link="/portal/dashboard/",
                    icon="gavel"
                )
                logger.info(f"[Degree Signal] Đã tạo Notification REVOKED cho sinh viên {student.user.username}")
            except Exception as ne:
                logger.warning(f"[Degree Signal] Không thể tạo Notification: {ne}")

    # Cập nhật lại trạng thái đã xử lý
    instance._previous_status = instance.status
