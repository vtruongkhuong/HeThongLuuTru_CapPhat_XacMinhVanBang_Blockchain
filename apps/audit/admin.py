from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(ModelAdmin):
    # Hiển thị trên bảng danh sách
    list_display = ('timestamp', 'actor', 'action', 'entity_type', 'entity_id', 'ip_address')
    
    # Bộ lọc bên phải
    list_filter = ('action', 'entity_type', 'timestamp')
    list_filter_submit = True
    
    # Khung tìm kiếm
    search_fields = ('actor__username', 'actor__email', 'entity_id', 'action', 'request_id')
    
    # Khóa toàn bộ các trường thành Chỉ-đọc
    readonly_fields = ('actor', 'action', 'entity_type', 'entity_id', 'old_value', 'new_value', 'ip_address', 'request_id', 'timestamp')

    # Chặn quyền Thêm, Sửa, Xóa để bảo toàn tính minh bạch của Log
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_module_permission(self, request):
        return True

    def has_view_permission(self, request, obj=None):
        return True