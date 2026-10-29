from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.urls import reverse
from apps.audit.services import log_action
from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import action, display
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from django.apps import apps
import pandas as pd
from datetime import datetime

from .models import Student, ImportBatch, ImportBatchItem

from .importers import process_excel_import as run_excel_import

def _read_gpa(row):
    """Đọc cột GPA. Rỗng -> None. Sai định dạng -> báo lỗi dòng."""
    for key in ('gpa', 'gpa_score', 'điểm gpa'):
        raw = row.get(key)
        if raw is not None and str(raw).strip().lower() not in ('', 'nan', 'none'):
            try:
                gpa = float(str(raw).strip().replace(',', '.'))
            except ValueError:
                raise ValueError(f"GPA không hợp lệ: '{raw}'")
            if not 0 <= gpa <= 4:
                raise ValueError(f"GPA phải từ 0 đến 4: '{raw}'")
            return gpa
    return None

def _read_dob(row):
    """Đọc cột Ngày sinh. Rỗng -> None."""
    for key in ('ngày sinh', 'date_of_birth', 'ngay sinh'):
        raw = row.get(key)
        if raw is None or str(raw).strip().lower() in ('', 'nan', 'nat', 'none'):
            continue
        if hasattr(raw, 'date'):           # pandas Timestamp / datetime
            return raw.date()
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
            try:
                return datetime.strptime(str(raw).strip()[:10], fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Không đọc được ngày sinh: '{raw}'")
    return None

class BaseRoleAdmin(ModelAdmin):
    """
    Class base chứa logic kiểm tra Role. 
    Chặn truy cập URL trực tiếp và ẩn menu đối với các cán bộ không có quyền.
    """
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


@admin.register(ImportBatch)
class ImportBatchAdmin(BaseRoleAdmin):
    allowed_roles = ['officer_a', 'academic_staff']
    list_display = ('id', 'file_name', 'batch', 'status_badge', 'imported_by', 'inserted', 'updated', 'errors', 'created_at', 'rollback_button')
    list_filter = ('mode',)
    list_filter_submit = True
    readonly_fields = ('inserted', 'updated', 'skipped', 'errors')

    actions = ['rollback_import_batch']

    @admin.action(description="🔄 Rollback (Hoàn tác) dữ liệu import này")
    def rollback_import_batch(self, request, queryset):
        # Kiểm tra quyền
        user_roles = request.user.roles.values_list('code', flat=True) if request.user.is_authenticated else []
        if 'officer_a' not in user_roles and not request.user.is_superuser:
            messages.error(request, "Bạn không có quyền thực hiện Rollback.")
            return

        success_count = 0
        error_count = 0

        for batch in queryset:
            # Kiểm tra trạng thái của GraduationBatch (Chỉ rollback nếu đợt duyệt đang DRAFT)
            if batch.batch.status.upper() != 'DRAFT':
                messages.warning(request, f"Không thể Rollback Import {batch.id} vì Đợt tốt nghiệp {batch.batch.name} không còn ở trạng thái Nháp (Draft).")
                error_count += 1
                continue

            try:
                with transaction.atomic():
                    # 1. Lấy tất cả các items thuộc batch này
                    items = batch.items.all().order_by('-row_number') # Rollback từ dưới lên để an toàn

                    for item in items:
                        if item.action == 'INSERT':
                            # Nếu import là INSERT, rollback nghĩa là XÓA sinh viên đó
                            Student.objects.filter(student_code=item.student_code).delete()
                        elif item.action == 'UPDATE' and item.old_value:
                            # Nếu import là UPDATE, rollback nghĩa là Khôi phục lại old_value
                            student = Student.objects.filter(student_code=item.student_code).first()
                            if student:
                                old_data = item.old_value
                                if old_data.get('full_name'): student.full_name = old_data['full_name']
                                if old_data.get('email'): student.email = old_data['email']
                                if old_data.get('gpa_score'): student.gpa_score = old_data['gpa_score']
                                if old_data.get('date_of_birth'): student.date_of_birth = old_data['date_of_birth']
                                # Phục hồi khoá ngoại Major (nếu cần)
                                if old_data.get('major'):
                                    Major = apps.get_model('academic', 'Major')
                                    major = Major.objects.filter(code=old_data['major']).first()
                                    if major:
                                        student.major = major
                                        student.faculty = major.faculty
                                student.save()
                    
                    # 2. Cập nhật trạng thái đợt import sang rolled_back
                    batch.status = 'rolled_back'
                    batch.save(update_fields=['status'])
                    
                    try:
                        log_action(
                            actor=request.user,
                            action='ROLLBACK',
                            entity_type='ImportBatch',
                            entity_id=str(batch.id),
                            old={'status': 'completed'},
                            new={'status': 'rolled_back'},
                            request=request
                        )
                    except Exception:
                        pass
                    success_count += 1
            except Exception as e:
                messages.error(request, f"Lỗi khi rollback batch {batch.id}: {str(e)}")
                error_count += 1

        if success_count > 0:
            messages.success(request, f"Đã hoàn tác (Rollback) thành công {success_count} đợt import.")
        if error_count > 0:
            messages.warning(request, f"Có {error_count} đợt import không thể hoàn tác.")

    def status_badge(self, obj):
        if obj.status == 'rolled_back':
            return mark_safe('<span style="background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600;">Đã hoàn tác</span>')
        return mark_safe('<span style="background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600;">Hoàn thành</span>')
    status_badge.short_description = "Trạng thái"

    def rollback_button(self, obj):
        if obj.status == 'rolled_back':
            return mark_safe('<span style="color: #9ca3af; font-size: 12px; font-style: italic;">Đã Rollback</span>')
        if obj.batch and obj.batch.status.upper() != 'DRAFT':
            return mark_safe('<span style="color: #9ca3af; font-size: 11px;" title="Đợt đã duyệt, không thể hoàn tác">Khóa</span>')
        url = reverse('admin:students_importbatch_single_rollback', args=[obj.id])
        return format_html(
            '<a href="{}" onclick="return confirm(&quot;Xác nhận hoàn tác (Rollback) đợt nạp này?&quot;);" style="background: #ef4444; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; text-decoration: none; display: inline-block;">🔄 Rollback</a>',
            url
        )
    rollback_button.short_description = "Hoàn tác"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:batch_id>/single-rollback/', self.admin_site.admin_view(self.process_single_rollback), name='students_importbatch_single_rollback'),
        ]
        return custom_urls + urls

    def process_single_rollback(self, request, batch_id):
        batch = self.get_object(request, batch_id)
        if not batch:
            messages.error(request, "Không tìm thấy đợt import.")
            return redirect('admin:students_importbatch_changelist')
        self.rollback_import_batch(request, [batch])
        return redirect('admin:students_importbatch_changelist')


@admin.register(ImportBatchItem)
class ImportBatchItemAdmin(BaseRoleAdmin):
    allowed_roles = ['officer_a', 'academic_staff']
    list_display = ('import_batch', 'row_number', 'student_code', 'action', 'error_message')
    list_filter = ('action',)
    list_filter_submit = True
    search_fields = ('student_code',)


@admin.register(Student)
class StudentAdmin(BaseRoleAdmin):
    allowed_roles = ['officer_a', 'academic_staff', 'officer_b', 'reviewer', 'approver']
    
    # --- CẤU HÌNH GIAO DIỆN DANH SÁCH ---
    list_display = ('student_code', 'full_name', 'faculty', 'major', 'display_status')
    list_filter = ('status', 'faculty', 'major', 'enrollment_year')
    list_filter_submit = True
    search_fields = ('student_code', 'full_name', 'national_id')
    autocomplete_fields = ['faculty', 'major']

    # --- 1. TÍNH NĂNG CỦA CÁN BỘ PHÊ DUYỆT (OFFICER B) ---
    actions = ['approve_selected_students']

    @display(
        description="Trạng thái",
        label={
            "draft": "warning",    # Nháp -> Màu cam/vàng
            "pending": "info",     # Chờ duyệt -> Màu xanh dương
            "approved": "success", # Đã duyệt -> Màu xanh lá
        },
    )
    def display_status(self, obj):
        return obj.status

    @admin.action(description="✅ Phê duyệt cấp bằng các hồ sơ đã chọn")
    def approve_selected_students(self, request, queryset):
        # Lớp bảo mật backend: Chặn Officer A tự ý bấm duyệt thông qua URL
        user_roles = request.user.roles.values_list('code', flat=True) if request.user.is_authenticated else []
        if 'officer_b' not in user_roles and 'approver' not in user_roles and not request.user.is_superuser:
            messages.error(request, "Cảnh báo: Bạn không có thẩm quyền phê duyệt danh sách này!")
            return

        # Chỉ duyệt những sinh viên đang ở trạng thái Nháp hoặc Chờ
        draft_students = queryset.filter(status__in=['draft', 'pending'])
        count = draft_students.count()

        if count == 0:
            messages.warning(request, "Không có hồ sơ nào hợp lệ để duyệt (Có thể đã được duyệt từ trước).")
            return

        draft_students.update(status='approved')
        messages.success(request, f"🎉 Đã phê duyệt thành công {count} hồ sơ sinh viên!")

    # Lớp bảo mật UI: Ẩn hoàn toàn nút phê duyệt khỏi giao diện đối với người không có quyền
    def get_actions(self, request):
        actions = super().get_actions(request)
        
        # Nếu là Superuser thì hiển thị tất cả, không cần kiểm tra
        if request.user.is_superuser:
            return actions

        # Lấy danh sách role của user hiện tại
        user_roles = request.user.roles.values_list('code', flat=True) if request.user.is_authenticated else []
        
        # Nếu user KHÔNG CÓ quyền officer_b và KHÔNG CÓ quyền approver -> Xóa nút phê duyệt
        if 'officer_b' not in user_roles and 'approver' not in user_roles:
            if 'approve_selected_students' in actions:
                del actions['approve_selected_students']
                
        return actions

    def get_readonly_fields(self, request, obj=None):
        # Lấy danh sách các trường read-only mặc định
        readonly_fields = list(super().get_readonly_fields(request, obj))
        
        # Nếu là Superuser thì được sửa thoải mái
        if request.user.is_superuser:
            return readonly_fields

        # Lấy danh sách role của user hiện tại
        user_roles = request.user.roles.values_list('code', flat=True) if request.user.is_authenticated else []
        
        # Nếu KHÔNG CÓ quyền duyệt, khóa chết cột 'status'
        if 'officer_b' not in user_roles and 'approver' not in user_roles:
            if 'status' not in readonly_fields:
                readonly_fields.append('status')
                
        return readonly_fields

    # --- 2. TÍNH NĂNG CỦA CÁN BỘ NHẬP LIỆU (OFFICER A) ---
    actions_list = ["import_excel_button"]

    @action(description="📥 Import Excel")
    def import_excel_button(self, request):
        return redirect('admin:students_import_excel')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-excel/', self.admin_site.admin_view(self.process_excel_import), name='students_import_excel'),
        ]
        return custom_urls + urls

    def process_excel_import(self, request):
        GraduationBatch = apps.get_model('graduation', 'GraduationBatch')
        
        if request.method == 'POST':
            excel_file = request.FILES.get('excel_file')
            batch_id = request.POST.get('batch_id')

            if not excel_file or not batch_id:
                messages.error(request, "Vui lòng chọn file Excel và Đợt tốt nghiệp.")
                return redirect('admin:students_import_excel')

            try:
                # GỌI LOGIC TỪ IMPORTERS.PY THAY VÌ VIẾT Ở ĐÂY
                batch_result = run_excel_import(excel_file, batch_id, request.user)
                
                messages.success(request, f"Import hoàn tất: {batch_result.inserted} mới, {batch_result.updated} cập nhật, {batch_result.skipped} bỏ qua, {batch_result.errors} lỗi.")
                return redirect('admin:students_importbatch_changelist')

            except Exception as e:
                messages.error(request, f"Lỗi xử lý file: {str(e)}")
                return redirect('admin:students_student_changelist')

        context = dict(
            self.admin_site.each_context(request),
            title="📥 Upload Danh sách Sinh viên",
            batches=GraduationBatch.objects.all()
        )
        return render(request, "admin/students/import_excel.html", context)