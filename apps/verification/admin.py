from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import VerificationLog


@admin.register(VerificationLog)
class VerificationLogAdmin(ModelAdmin):
    list_display = (
        'created_at', 
        'search_query', 
        'result_status', 
        'verification_type', 
        'degree', 
        'ip_address', 
        'is_successful'
    )
    
    list_filter = ('result_status', 'verification_type', 'is_successful', 'created_at')
    list_filter_submit = True
    
    # Phân trang và tối ưu hiệu năng cơ sở dữ liệu
    list_per_page = 25
    list_select_related = ('degree', 'degree__student')
    date_hierarchy = 'created_at'
    show_full_result_count = False
    
    search_fields = (
        'search_query', 
        'ip_address', 
        'degree__credential_public_id', 
        'degree__student__student_code', 
        'degree__student__full_name'
    )
    
    readonly_fields = (
        'search_query', 
        'degree', 
        'ip_address', 
        'user_agent', 
        'is_successful', 
        'created_at', 
        'result_status', 
        'verification_type'
    )

    # Chặn Thêm/Sửa để bảo toàn tính toàn vẹn của lịch sử tra cứu
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_module_permission(self, request):
        return True

    def has_view_permission(self, request, obj=None):
        return True
