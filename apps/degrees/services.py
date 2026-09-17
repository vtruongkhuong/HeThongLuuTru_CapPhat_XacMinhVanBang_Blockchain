from django.utils import timezone
from .models import Degree
from apps.blockchain.services import generate_canonical_hash, build_merkle_root

def submit_degree_for_approval(degree_id, user):
    """
    Bước 1: Cán bộ giáo vụ (Maker) tạo và trình duyệt văn bằng.
    """
    degree = Degree.objects.get(id=degree_id)
    
    if degree.status not in ['DRAFT', 'GENERATED']:
        raise ValueError("Chỉ có thể trình duyệt văn bằng ở trạng thái Nháp hoặc Đã tạo phôi.")
        
    # Ghi nhận Cán bộ là người trình (Người mắt thứ 1 & 2)
    degree.reviewed_by = user
    degree.reviewed_at = timezone.now()
    degree.status = 'REVIEWED'
    degree.save()
    
    return True, "Đã gửi yêu cầu phê duyệt văn bằng."


def approve_degree(degree_id, user):
    """
    Bước 2: Lãnh đạo (Checker) vào kiểm tra và phê duyệt.
    """
    degree = Degree.objects.get(id=degree_id)
    
    if degree.status != 'REVIEWED':
        raise ValueError("Văn bằng chưa được trình duyệt, không thể phê duyệt.")
        
    # LUẬT 4 MẮT (FOUR-EYES PRINCIPLE) - CHỐT CHẶN CỐT LÕI
    if degree.reviewed_by == user:
        raise PermissionError("Luật 4 mắt: Bạn không thể tự phê duyệt văn bằng do chính mình trình!")
        
    # TODO: Thêm logic kiểm tra quyền (Role) của user có phải là Lãnh đạo không ở đây
        
    # Ghi nhận Lãnh đạo là người duyệt (Người mắt thứ 3 & 4)
    degree.approved_by = user
    degree.approved_at = timezone.now()
    degree.status = 'APPROVED'
    degree.save()
    
    return True, "Phê duyệt văn bằng thành công. Sẵn sàng tạo Hash."