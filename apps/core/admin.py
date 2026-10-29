from unfold.admin import ModelAdmin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

def format_crypto_hash_badge(full_hash, title_prefix="Mã Merkle Root", icon="tag"):
    """
    Hàm định dạng mã băm chuỗi khối (Merkle Root, TxHash, Public ID) chuẩn Apple Design:
    - Hiển thị tương phản cao tuyệt đối cả Light & Dark mode (không bị mờ trắng).
    - Tích hợp tính năng Click-to-Copy với phản hồi trực quan sinh động.
    - Rút gọn 8 ký tự đầu...8 ký tự cuối.
    - An toàn tuyệt đối khi giá trị None hoặc rỗng (trả về mark_safe).
    """
    EMPTY_BADGE = mark_safe('<span class="text-gray-400 dark:text-gray-600 font-mono text-xs">-</span>')

    if not full_hash:
        return EMPTY_BADGE
    
    full_str = str(full_hash).strip()
    if not full_str or full_str == '-':
        return EMPTY_BADGE

    short_hash = f"{full_str[:8]}...{full_str[-8:]}" if len(full_str) > 20 else full_str
    
    inline_js = (
        f"navigator.clipboard.writeText('{full_str}');"
        "this.classList.add('copied');"
        "const orig = this.innerHTML;"
        "this.innerHTML = '<span class=\"material-symbols-outlined\" style=\"font-size:13px;\">check</span> Đã chép!';"
        "setTimeout(() => { this.innerHTML = orig; this.classList.remove('copied'); }, 1500);"
    )
    
    return format_html(
        '<button type="button" class="merkle-hash-badge apple-hash-pill" '
        'title="Nhấn để chép {}: {}" '
        'onclick="{}">'
        '<span class="material-symbols-outlined" style="font-size: 13px; opacity: 0.85;">{}</span>'
        '<span>{}</span>'
        '</button>',
        title_prefix, full_str, inline_js, icon, short_hash
    )

class BaseRoleAdmin(ModelAdmin):
    """Class base phân quyền dùng chung cho toàn dự án."""
    allowed_roles = []

    def _has_role(self, request):
        if request.user.is_superuser:
            return True
        user_roles = request.user.roles.values_list('code', flat=True) if request.user.is_authenticated else []
        return any(role in user_roles for role in self.allowed_roles)

    def has_module_permission(self, request):
        return self._has_role(request)

    def has_view_permission(self, request, obj=None):
        return self._has_role(request)

    def has_add_permission(self, request):
        return self._has_role(request)
        
    def has_change_permission(self, request, obj=None):
        return self._has_role(request)
        
    def has_delete_permission(self, request, obj=None):
        return self._has_role(request)
