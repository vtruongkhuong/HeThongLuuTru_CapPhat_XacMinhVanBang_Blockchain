from .models import Degree
from apps.workflow.services import transition


def submit_degree_for_approval(degree_id, user):
    """
    Bước 1: Cán bộ giáo vụ (Maker) trình duyệt văn bằng.
    Chuyển trạng thái DRAFT/GENERATED → REVIEWED.
    """
    degree = Degree.objects.get(id=degree_id)
    if degree.status not in ('DRAFT', 'GENERATED'):
        raise ValueError("Chỉ có thể trình duyệt văn bằng ở trạng thái Nháp hoặc Đã tạo phôi.")
    transition(degree, 'REVIEWED', actor=user)
    return True, "Đã gửi yêu cầu phê duyệt văn bằng."

def approve_degree(degree_id, user):
    """
    Bước 2: Lãnh đạo (Checker) phê duyệt văn bằng.
    Chuyển trạng thái REVIEWED → APPROVED.
    Áp dụng quy tắc 4-eyes: người duyệt phải khác người trình (reviewer).
    """
    degree = Degree.objects.get(id=degree_id)
    if degree.status != 'REVIEWED':
        raise ValueError("Văn bằng chưa được trình duyệt, không thể phê duyệt.")
    # transition() sẽ tự kiểm tra 4-eyes (reviewed_by ≠ actor)
    transition(degree, 'APPROVED', actor=user)
    return True, "Phê duyệt văn bằng thành công. Sẵn sàng phát hành."