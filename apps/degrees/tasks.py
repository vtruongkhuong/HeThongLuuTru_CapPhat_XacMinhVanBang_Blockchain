"""
Celery Background Job - Render PDF hàng loạt cho hệ thống phát hành văn bằng.
(Task H6)
"""
import os
import hashlib
from datetime import datetime
from celery import shared_task
from django.conf import settings
from django.db import transaction

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
                leaf_data = {
                    "credential_public_id": str(degree.credential_public_id),
                    "student_code": degree.student.student_code,
                    "degree_type_code": degree.degree_type.code if degree.degree_type else "CN",
                }
                degree.canonical_hash = canonical_hash(leaf_data)

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
