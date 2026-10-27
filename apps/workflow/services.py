from django.utils import timezone
from django.core.exceptions import ValidationError

# ─────────────────────────────────────────────
#  BẢNG CHUYỂN TRẠNG THÁI HỢP LỆ
# ─────────────────────────────────────────────
VALID_TRANSITIONS = {
    'DRAFT':            ['GENERATED', 'REVIEWED'],
    'GENERATED':        ['REVIEWED', 'DRAFT'],
    'REVIEWED':         ['APPROVED', 'DRAFT'],
    'APPROVED':         ['ISSUANCE_PENDING'],
    'ISSUANCE_PENDING': ['ISSUED', 'APPROVED'],   # APPROVED = cho phép retry
    'ISSUED':           ['REVOKED'],
    'REVOKED':          [],                        # trạng thái cuối, không đổi nữa
}
# ─────────────────────────────────────────────
#  4-EYES RULE
# ──────────────────────────────────────────

def ensure_different_actors(*users):
    """
    Kiểm tra quy tắc 4-eyes (hoặc n-eyes): Đảm bảo các tác nhân thực hiện
    các bước trong một quy trình là những người hoàn toàn khác nhau.
    
    Args:
        *users: Danh sách các đối tượng User truyền vào (có thể chứa None nếu bước đó chưa xảy ra).
        
    Raises:
        ValidationError: Nếu phát hiện một người thực hiện nhiều hơn một bước.
    """
    
    # 1. Lọc bỏ các giá trị None (những bước chưa có người thực hiện)
    active_users = [u for u in users if u is not None]
    
    # 2. Nếu chưa có ai thực hiện hoặc mới có 1 người thực hiện thì hợp lệ
    if len(active_users) <= 1:
        return True
        
    # 3. Lấy ra danh sách ID của những người đã thực hiện
    user_ids = [u.id for u in active_users]
    
    # 4. Dùng set() để loại bỏ các ID trùng lặp. 
    # Nếu số lượng ID sau khi lọc nhỏ hơn số lượng ID ban đầu => Có người trùng nhau!
    if len(user_ids) != len(set(user_ids)):
        raise ValidationError(
            "Một tài khoản không được phép "
            "thực hiện nhiều bước (Tạo/Duyệt/Thực thi) trong cùng một quy trình!"
        )
        
    return True


def transition(degree, to_status: str, actor):
    """
    Chuyển trạng thái Degree một cách an toàn.
    Thực hiện theo thứ tự:
      1. Kiểm tra chuyển trạng thái có hợp lệ không.
      2. Áp dụng quy tắc 4-eyes khi bước APPROVED (reviewer ≠ approver).
      3. Cập nhật status và các trường tracking (reviewed_by, approved_by, ...).
      4. Lưu DB.
      5. Ghi AuditLog (nếu module audit đã có).
    Args:
        degree   : đối tượng Degree cần chuyển trạng thái.
        to_status: trạng thái đích (phải nằm trong VALID_TRANSITIONS).
        actor    : User đang thực hiện hành động.
    Returns:
        degree đã được cập nhật.
    Raises:
        ValidationError: nếu chuyển trạng thái không hợp lệ hoặc vi phạm 4-eyes.
    """
    from_status = degree.status

    # ── 1. Kiểm tra chuyển trạng thái
    allowed = VALID_TRANSITIONS.get(from_status, [])
    if to_status not in allowed:
        raise ValidationError(
            f"Không thể chuyển Degree từ '{from_status}' sang '{to_status}'. "
            f"Các trạng thái hợp lệ từ '{from_status}': {allowed or ['(không có)']}"
        )
    # ── 2. Quy tắc 4-eyes khi APPROVED 
    if to_status == 'APPROVED':
        ensure_different_actors(degree.reviewed_by, actor)
    # ── 3. Cập nhật các trường tracking 
    old_status = degree.status
    degree.status = to_status
    if to_status == 'REVIEWED':
        degree.reviewed_by = actor
        degree.reviewed_at = timezone.now()
    elif to_status == 'APPROVED':
        degree.approved_by = actor
        degree.approved_at = timezone.now()
    # ── 4. Lưu DB 
    degree.save()
    # ── 5. Ghi AuditLog 
    _safe_audit_log(
        actor=actor,
        action=f'DEGREE_{to_status}',
        entity_type='Degree',
        entity_id=str(degree.pk),
        old={'status': old_status},
        new={'status': to_status},
    )
    return degree
# ─────────────────────────────────────────────
#  HELPER NỘI BỘ
# ─────────────────────────────────────────────
def _safe_audit_log(**kwargs):
    """Ghi audit log nếu module audit đã có, không báo lỗi nếu chưa."""
    try:
        from apps.audit.services import log_action
        log_action(**kwargs)
    except Exception:
        pass
    return True