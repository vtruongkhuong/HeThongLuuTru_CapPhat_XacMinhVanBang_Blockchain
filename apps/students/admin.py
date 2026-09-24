from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Student, ImportBatch, ImportBatchItem


class BaseRoleAdmin(ModelAdmin):
    """
    Class base chứa logic kiểm tra Role. 
    Chặn truy cập URL trực tiếp và ẩn menu đối với các cán bộ không có quyền.
    """
    allowed_roles = [] # Khai báo danh sách mã role (code) được phép vào

    def _has_role(self, request):
        if request.user.is_superuser:
            return True
        # Lấy danh sách các role (ví dụ: 'officer_a', 'issuer') của user đang đăng nhập
        user_roles = request.user.roles.values_list('code', flat=True)
        return any(role in user_roles for role in self.allowed_roles)

    def has_module_permission(self, request):
        # Ẩn/Hiện menu bên thanh Sidebar của Unfold
        return self._has_role(request)

    def has_view_permission(self, request, obj=None):
        return self._has_role(request)

    def has_add_permission(self, request):
        return self._has_role(request)
        
    def has_change_permission(self, request, obj=None):
        return self._has_role(request)
        
    def has_delete_permission(self, request, obj=None):
        return self._has_role(request)


@admin.register(Student)
class StudentAdmin(BaseRoleAdmin):
    # Danh sách sinh viên: Cả Officer A (nhập liệu) và Officer B (duyệt) đều cần xem
    allowed_roles = ['officer_a', 'academic_staff', 'officer_b', 'reviewer', 'approver']
    
    list_display = ('student_code', 'full_name', 'faculty', 'major', 'enrollment_year')
    list_filter = ('faculty', 'major', 'enrollment_year')
    list_filter_submit = True
    search_fields = ('student_code', 'full_name', 'national_id')
    autocomplete_fields = ['faculty', 'major']


@admin.register(ImportBatch)
class ImportBatchAdmin(BaseRoleAdmin):
    # Lịch sử Import: CHỈ dành riêng cho Cán bộ nhập liệu (Officer A)
    allowed_roles = ['officer_a', 'academic_staff']
    
    list_display = ('id', 'file_name', 'batch', 'imported_by', 'mode', 'inserted', 'updated', 'errors', 'created_at')
    list_filter = ('mode',)
    list_filter_submit = True
    readonly_fields = ('inserted', 'updated', 'skipped', 'errors')


@admin.register(ImportBatchItem)
class ImportBatchItemAdmin(BaseRoleAdmin):
    # Chi tiết Import: CHỈ dành riêng cho Cán bộ nhập liệu (Officer A)
    allowed_roles = ['officer_a', 'academic_staff']
    
    list_display = ('import_batch', 'row_number', 'student_code', 'action', 'error_message')
    list_filter = ('action',)
    list_filter_submit = True
    search_fields = ('student_code',)