import os
import hashlib
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from django.db import transaction

from .models import Degree
from .canonicalizer import degree_leaf_hash
from .pdf_generator import get_degree_pdf
from apps.workflow.services import transition, ensure_different_actors
from apps.blockchain.models import IssuanceBatch, DegreeMerkleProof


def submit_degree_for_approval(degree_id, user):
    """
    Bước 1: Cán bộ giáo vụ (Maker) trình duyệt văn bằng đơn lẻ.
    Chuyển trạng thái DRAFT/GENERATED → REVIEWED.
    """
    degree = Degree.objects.get(id=degree_id)
    if degree.status not in ('DRAFT', 'GENERATED'):
        raise ValueError("Chỉ có thể trình duyệt văn bằng ở trạng thái Nháp hoặc Đã tạo phôi.")
    
    transition(degree, 'REVIEWED', actor=user)
    return True, "Đã gửi yêu cầu phê duyệt văn bằng."


def approve_degree(degree_id, user):
    """
    Bước 2: Lãnh đạo (Checker) phê duyệt văn bằng đơn lẻ.
    Chuyển trạng thái REVIEWED → APPROVED.
    Áp dụng quy tắc 4-eyes: người duyệt phải khác người trình (reviewer).
    Tự động sinh Canonical Hash (có kèm GPA), tạo IssuanceBatch đơn lẻ, và sinh file PDF.
    """
    degree = Degree.objects.select_related('student', 'batch', 'degree_type').get(id=degree_id)
    if degree.status != 'REVIEWED':
        raise ValueError("Văn bằng chưa được trình duyệt, không thể phê duyệt.")

    # 1. Chuyển trạng thái (kiểm tra 4-eyes trong transition)
    transition(degree, 'APPROVED', actor=user)

    # 2. Sinh Canonical Hash chuẩn hóa nếu chưa có (đã bao gồm GPA)
    if not degree.canonical_hash:
        degree.canonical_hash = degree_leaf_hash(degree)

    # 3. Kết xuất PDF ngay lập tức
    media_root = getattr(settings, 'MEDIA_ROOT', os.path.join(settings.BASE_DIR, 'media'))
    degree_media_dir = os.path.join(media_root, 'degrees')
    os.makedirs(degree_media_dir, exist_ok=True)

    type_code = degree.degree_type.code if degree.degree_type else "DEG"
    file_name = f"{type_code}_{degree.student.student_code}_{degree.credential_public_id}.pdf"
    file_path = os.path.join(degree_media_dir, file_name)

    pdf_bytes = get_degree_pdf(degree)
    if pdf_bytes:
        with open(file_path, 'wb') as f:
            f.write(pdf_bytes)
        degree.pdf_path = f"degrees/{file_name}"
        degree.pdf_sha256 = hashlib.sha256(pdf_bytes).hexdigest()
        degree.generated_at = timezone.now()

    degree.save()

    # 4. Tạo hoặc liên kết IssuanceBatch đơn lẻ (Cây Merkle 1 lá: Root chính là Leaf Hash)
    single_batch, _ = IssuanceBatch.objects.get_or_create(
        graduation_batch=degree.batch,
        merkle_root=degree.canonical_hash,
        defaults={'status': 'PENDING'}
    )

    # 5. Lưu Merkle Proof cho văn bằng đơn lẻ (proof_path = [] vì chỉ có 1 lá)
    DegreeMerkleProof.objects.update_or_create(
        degree=degree,
        defaults={
            'issuance_batch': single_batch,
            'leaf_hash': degree.canonical_hash,
            'leaf_index': 0,
            'proof_path': []
        }
    )

    try:
        from apps.audit.services import log_action
        log_action(
            actor=user,
            action='APPROVE_BATCH',
            entity_type='Degree',
            entity_id=str(degree.id),
            new={'status': 'APPROVED', 'canonical_hash': degree.canonical_hash}
        )
    except Exception:
        pass

    return True, single_batch
