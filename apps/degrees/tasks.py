"""
Celery Background Job - Render PDF hàng loạt cho hệ thống phát hành văn bằng.
(Task H6)
"""
import os
import io
import base64
import hashlib
from datetime import datetime
from email.mime.image import MIMEImage
import qrcode
from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

# Gọi model từ các app tương ứng
from .models import Degree
from .pdf_generator import get_degree_pdf
from .canonicalizer import canonical_hash


@shared_task(bind=True)
def render_degree_pdfs(self, batch_id, actor_id=None):
    """
    Task render PDF hàng loạt nền.
    Lấy tất cả các văn bằng đang ở trạng thái DRAFT / APPROVED / GENERATED của một batch nhất định,
    render ra PDF, lưu file, tính pdf_sha256 và chuyển sang GENERATED.
    """
    actor = None
    if actor_id:
        try:
            from django.contrib.auth import get_user_model
            actor = get_user_model().objects.filter(id=actor_id).first()
        except Exception:
            pass

    degrees = Degree.objects.filter(batch_id=batch_id, status__in=['DRAFT', 'APPROVED', 'GENERATED'])
    total = degrees.count()
    success_count = 0
    error_count = 0

    # Khai báo đường dẫn thư mục lưu trữ (tương đương media/degrees/)
    media_root = getattr(settings, 'MEDIA_ROOT', os.path.join(settings.BASE_DIR, 'media'))
    degree_media_dir = os.path.join(media_root, 'degrees')
    
    # Tạo thư mục nếu chưa tồn tại
    if not os.path.exists(degree_media_dir):
        os.makedirs(degree_media_dir, exist_ok=True)

    for i, degree in enumerate(degrees, 1):
        try:
            # 1. Sinh Canonical Hash tạm thời nếu chưa có
            if not degree.canonical_hash:
                from .canonicalizer import degree_leaf_hash
                degree.canonical_hash = degree_leaf_hash(degree)

            # 2. Gọi logic Render PDF từ pdf_generator.py (Tự phân luồng 4 template CN, KS, THVP, CNTT)
            pdf_bytes = get_degree_pdf(degree)

            if not pdf_bytes:
                raise Exception("Kết xuất PDF lỗi. Hàm get_degree_pdf trả về rỗng.")

            # 3. Tạo đường dẫn và lưu File
            type_code = degree.degree_type.code if degree.degree_type else "DEG"
            file_name = f"{type_code}_{degree.student.student_code}_{degree.credential_public_id}.pdf"
            file_path = os.path.join(degree_media_dir, file_name)
            
            with open(file_path, 'wb') as f:
                f.write(pdf_bytes)

            # 4. Tính toán pdf_sha256 từ file vật lý 
            file_sha256 = hashlib.sha256(pdf_bytes).hexdigest()

            # 5. Cập nhật Model trong 1 transaction an toàn
            with transaction.atomic():
                degree.pdf_path = f"degrees/{file_name}"
                degree.pdf_sha256 = file_sha256
                degree.generated_at = datetime.now()
                degree.status = 'GENERATED'
                
                # Tải lên IPFS phi tập trung
                try:
                    from apps.blockchain.ipfs import pin_file_to_ipfs
                    cid, gateway_url = pin_file_to_ipfs(pdf_bytes, file_name=file_name)
                    degree.ipfs_cid = cid
                    degree.ipfs_url = gateway_url
                except Exception as ipfs_err:
                    print(f"[IPFS Task Error] {ipfs_err}")

                degree.save()

            success_count += 1

            # Update Celery State (dùng để tạo thanh tiến trình trên giao diện)
            try:
                self.update_state(state='PROGRESS', meta={'current': i, 'total': total})
            except Exception:
                pass

        except Exception as e:
            error_count += 1
            print(f"[Render PDF Error] ID: {degree.id} - Lỗi: {str(e)}")

    try:
        from apps.audit.services import log_action
        log_action(
            actor=actor,
            action='RENDER_PDF',
            entity_type='GraduationBatch',
            entity_id=str(batch_id),
            new={'total': total, 'success': success_count, 'errors': error_count}
        )
    except Exception as e:
        print(f"[AuditLog Render Error] {e}")

    return {
        'status': 'Completed',
        'total': total,
        'success': success_count,
        'errors': error_count,
    }


@shared_task(bind=True)
def send_degree_congratulation_email(self, degree_id):
    """
    Task Celery tự động gửi email chúc mừng kèm file PDF văn bằng và mã QR
    cho sinh viên ngay khi văn bằng được duyệt On-Chain.
    """
    try:
        degree = Degree.objects.select_related('student', 'batch', 'degree_type', 'student__major').get(id=degree_id)
    except Degree.DoesNotExist:
        return {'status': 'error', 'message': f'Degree #{degree_id} không tồn tại'}

    student = degree.student
    if not student or not student.email:
        return {'status': 'skipped', 'message': f'Sinh viên {getattr(student, "student_code", "N/A")} chưa có email'}

    site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000').rstrip('/')
    verify_url = f"{site_url}/tracuu/?q={degree.credential_public_id}"

    # 1. Sinh mã QR code tra cứu (PNG bytes)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2
    )
    qr.add_data(verify_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#1E3A8A", back_color="white")
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, format="PNG")
    qr_bytes = qr_buf.getvalue()
    qr_base64 = base64.b64encode(qr_bytes).decode('ascii')

    # 2. Lấy nội dung file PDF văn bằng
    pdf_bytes = None
    media_root = getattr(settings, 'MEDIA_ROOT', os.path.join(settings.BASE_DIR, 'media'))
    if degree.pdf_path:
        full_pdf_path = os.path.join(media_root, degree.pdf_path.replace('/', os.sep))
        if os.path.exists(full_pdf_path):
            with open(full_pdf_path, 'rb') as f:
                pdf_bytes = f.read()

    if not pdf_bytes:
        pdf_bytes = get_degree_pdf(degree)

    # 3. Render HTML Email
    context = {
        'student': student,
        'degree': degree,
        'verify_url': verify_url,
        'qr_base64': qr_base64,
    }
    html_content = render_to_string('emails/degree_issued_congratulation.html', context)
    text_content = strip_tags(html_content)

    subject = f"[CTUT] Chúc mừng tốt nghiệp - Văn bằng số đã được cấp phát & xác thực Blockchain ({student.student_code})"
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Phòng Đào Tạo CTUT <daotao@ctuet.edu.vn>')

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=from_email,
        to=[student.email]
    )
    msg.attach_alternative(html_content, "text/html")

    # 4. Đính kèm mã QR dạng CID Image
    try:
        qr_part = MIMEImage(qr_bytes, _subtype="png")
        qr_part.add_header('Content-ID', '<degree_qr_code>')
        qr_part.add_header('Content-Disposition', 'inline', filename='qr_code.png')
        msg.attach(qr_part)
    except Exception as qr_err:
        print(f"[Email QR Attach Warning] {qr_err}")

    # 5. Đính kèm file PDF văn bằng
    if pdf_bytes:
        type_code = degree.degree_type.code if degree.degree_type else 'DEG'
        pdf_filename = f"VanBang_{student.student_code}_{type_code}.pdf"
        msg.attach(pdf_filename, pdf_bytes, "application/pdf")

    # 6. Gửi email
    try:
        msg.send(fail_silently=False)
    except Exception as send_err:
        print(f"[Email Send Error] {send_err}")
        return {'status': 'error', 'message': str(send_err)}

    # 7. Ghi AuditLog
    try:
        from apps.audit.services import log_action
        log_action(
            actor=None,
            action='SEND_EMAIL',
            entity_type='Degree',
            entity_id=str(degree.id),
            new={'recipient': student.email, 'status': 'SENT', 'student_code': student.student_code}
        )
    except Exception:
        pass

    return {
        'status': 'success',
        'degree_id': degree.id,
        'recipient': student.email,
        'student_code': student.student_code
    }


@shared_task
def send_batch_congratulation_emails(batch_id):
    """
    Task gửi email hàng loạt cho toàn bộ văn bằng ISSUED trong 1 đợt tốt nghiệp.
    """
    degrees = Degree.objects.filter(batch_id=batch_id, status='ISSUED')
    sent_count = 0
    for d in degrees:
        send_degree_congratulation_email.delay(d.id)
        sent_count += 1
    return {'batch_id': batch_id, 'sent_count': sent_count}

