"""
Email Service: Dịch vụ gửi email thông báo tự động cho hệ thống Văn bằng số CTUT.
- Cấp bằng (Issued Congratulation)
- Thu hồi bằng (Revocation Notice)
- Chia sẻ liên kết hồ sơ (Share Link Notification)
"""
import os
import io
import base64
import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def _get_from_email():
    """Lấy địa chỉ người gửi mặc định từ settings"""
    return getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'EMAIL_HOST_USER', 'daotao@ctuet.edu.vn')


def send_degree_issued_email(degree):
    """
    Gửi email chúc mừng và cung cấp thông tin văn bằng số, mã tra cứu, QR code
    kèm bản PDF chính thức khi trạng thái văn bằng chuyển sang ISSUED.
    """
    student = getattr(degree, 'student', None)
    if not student or not getattr(student, 'email', None):
        logger.warning(f"[Email Service] Sinh viên của văn bằng #{degree.id} không có địa chỉ email hợp lệ.")
        return False

    try:
        verify_url = f"http://127.0.0.1:8000/verify/tracuu/?q={degree.credential_public_id}"

        # 1. Sinh QR Code dạng base64
        qr_base64 = ""
        try:
            import qrcode
            qr = qrcode.QRCode(version=1, box_size=8, border=2)
            qr.add_data(verify_url)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="#1E3A8A", back_color="white")
            qr_buf = io.BytesIO()
            qr_img.save(qr_buf, format="PNG")
            qr_base64 = base64.b64encode(qr_buf.getvalue()).decode('ascii')
        except Exception as qr_err:
            logger.warning(f"[Email Service] Lỗi tạo QR cho email: {qr_err}")

        # 2. Render Template
        context = {
            'degree': degree,
            'student': student,
            'verify_url': verify_url,
            'qr_base64': qr_base64,
        }
        html_content = render_to_string('emails/degree_issued_congratulation.html', context)
        text_content = strip_tags(html_content)

        subject = f"[CTUT] Văn bằng của bạn đã được cấp phát thành công ({student.student_code})"
        from_email = _get_from_email()

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[student.email]
        )
        email.attach_alternative(html_content, 'text/html')

        # 3. Đính kèm PDF văn bằng nếu có
        try:
            pdf_bytes = None
            media_root = getattr(settings, 'MEDIA_ROOT', os.path.join(settings.BASE_DIR, 'media'))
            if getattr(degree, 'pdf_path', None):
                full_pdf_path = os.path.join(media_root, degree.pdf_path.replace('/', os.sep))
                if os.path.exists(full_pdf_path):
                    with open(full_pdf_path, 'rb') as f:
                        pdf_bytes = f.read()

            if not pdf_bytes:
                from .pdf_generator import get_degree_pdf
                pdf_bytes = get_degree_pdf(degree)

            if pdf_bytes:
                type_code = degree.degree_type.code if degree.degree_type else 'DEG'
                pdf_filename = f"VanBang_{student.student_code}_{type_code}.pdf"
                email.attach(pdf_filename, pdf_bytes, "application/pdf")
        except Exception as pdf_err:
            logger.warning(f"[Email Service] Không thể đính kèm PDF: {pdf_err}")

        # 4. Gửi email
        email.send(fail_silently=True)
        logger.info(f"[Email Service] Đã gửi email cấp bằng thành công tới: {student.email}")
        return True

    except Exception as exc:
        logger.error(f"[Email Service] Lỗi gửi email cấp bằng cho {student.email}: {exc}")
        return False


def send_degree_revoked_email(degree, reason=None):
    """
    Gửi email cảnh báo và thông báo thu hồi văn bằng khi trạng thái chuyển sang REVOKED.
    """
    student = getattr(degree, 'student', None)
    if not student or not getattr(student, 'email', None):
        logger.warning(f"[Email Service] Sinh viên của văn bằng #{degree.id} không có địa chỉ email hợp lệ.")
        return False

    try:
        # Chuẩn hóa mô tả lý do thu hồi
        reason_text = ""
        if isinstance(reason, str):
            reason_text = reason
        elif hasattr(reason, 'description') and reason.description:
            if hasattr(reason, 'reason_code') and reason.reason_code:
                desc = getattr(reason.reason_code, 'description', str(reason.reason_code))
                reason_text = f"{desc}: {reason.description}"
            else:
                reason_text = reason.description
        elif hasattr(reason, 'reason_code') and reason.reason_code:
            reason_text = getattr(reason.reason_code, 'description', str(reason.reason_code))
        
        if not reason_text:
            reason_text = "Quyết định xử lý kỷ luật từ Hội đồng Trường & Phòng Đào tạo"

        context = {
            'degree': degree,
            'student': student,
            'reason': reason_text,
        }
        html_content = render_to_string('emails/degree_revoked_notice.html', context)
        text_content = strip_tags(html_content)

        serial = getattr(degree, 'degree_number', None) or getattr(degree, 'serial_number', str(degree.id))
        subject = f"[CTUT] CẢNH BÁO: Văn bằng số {serial} đã bị thu hồi ({student.student_code})"
        from_email = _get_from_email()

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[student.email]
        )
        email.attach_alternative(html_content, 'text/html')
        email.send(fail_silently=True)

        logger.info(f"[Email Service] Đã gửi email thông báo thu hồi bằng tới: {student.email}")
        return True

    except Exception as exc:
        logger.error(f"[Email Service] Lỗi gửi email thu hồi cho {student.email}: {exc}")
        return False


def send_share_link_email(student, share_link, share_url=None):
    """
    Gửi email thông báo cho sinh viên khi tạo thành công liên kết chia sẻ hồ sơ (cho nhà tuyển dụng).
    """
    if not student or not getattr(student, 'email', None):
        logger.warning("[Email Service] Sinh viên không có địa chỉ email hợp lệ để nhận share link.")
        return False

    try:
        if not share_url:
            from django.urls import reverse
            try:
                share_url = f"http://127.0.0.1:8000{reverse('student_portal:public_shared_profile', args=[share_link.token])}"
            except Exception:
                share_url = f"http://127.0.0.1:8000/portal/share/{share_link.token}/"

        context = {
            'student': student,
            'share_link': share_link,
            'share_url': share_url,
        }
        html_content = render_to_string('emails/share_link.html', context)
        text_content = strip_tags(html_content)

        subject = f"[CTUT] Thông báo tạo liên kết chia sẻ hồ sơ văn bằng ({student.student_code})"
        from_email = _get_from_email()

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[student.email]
        )
        email.attach_alternative(html_content, 'text/html')
        email.send(fail_silently=True)

        logger.info(f"[Email Service] Đã gửi email xác nhận share link tới: {student.email}")
        return True

    except Exception as exc:
        logger.error(f"[Email Service] Lỗi gửi email share link cho {student.email}: {exc}")
        return False
