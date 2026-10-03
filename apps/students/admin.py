from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import action, display
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from django.apps import apps
import pandas as pd

from .models import Student, ImportBatch, ImportBatchItem

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
    list_display = ('id', 'file_name', 'batch', 'imported_by', 'mode', 'inserted', 'updated', 'errors', 'created_at')
    list_filter = ('mode',)
    list_filter_submit = True
    readonly_fields = ('inserted', 'updated', 'skipped', 'errors')


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
        Major = apps.get_model('academic', 'Major') 
        
        if request.method == 'POST':
            excel_file = request.FILES.get('excel_file')
            batch_id = request.POST.get('batch_id')

            if not excel_file or not batch_id:
                messages.error(request, "Vui lòng chọn file Excel và Đợt tốt nghiệp.")
                return redirect('admin:students_import_excel')

            try:
                batch_obj = GraduationBatch.objects.get(pk=batch_id)
                df = pd.read_excel(excel_file)
                df.columns = df.columns.str.strip().str.lower()
                
                import_batch = ImportBatch.objects.create(
                    batch=batch_obj,
                    file_name=excel_file.name,
                    imported_by=request.user,
                    mode='PARTIAL'
                )

                inserted_count = updated_count = error_count = 0

                with transaction.atomic():
                    for index, row in df.iterrows():
                        mssv = str(row.get('mã sv', '')).strip()
                        ho_ten = str(row.get('họ tên', '')).strip()
                        ma_nganh = str(row.get('mã ngành', '')).strip()
                        
                        if not mssv or mssv == 'nan':
                            continue 

                        try:
                            major_obj = Major.objects.filter(code=ma_nganh).first()
                            if not major_obj:
                                raise ValueError(f"Không tìm thấy mã ngành: {ma_nganh}")

                            student, created = Student.objects.update_or_create(
                                student_code=mssv,
                                defaults={
                                    'full_name': ho_ten,
                                    'major': major_obj,
                                    'faculty': major_obj.faculty
                                }
                            )
                            
                            action_type = 'INSERT' if created else 'UPDATE'
                            if created: inserted_count += 1
                            else: updated_count += 1

                            ImportBatchItem.objects.create(
                                import_batch=import_batch,
                                row_number=index + 2,
                                student_code=mssv,
                                action=action_type,
                                new_value={'full_name': ho_ten, 'major': ma_nganh}
                            )

                        except Exception as row_err:
                            error_count += 1
                            ImportBatchItem.objects.create(
                                import_batch=import_batch,
                                row_number=index + 2,
                                student_code=mssv,
                                action='ERROR',
                                error_message=str(row_err)[:250] 
                            )

                import_batch.inserted = inserted_count
                import_batch.updated = updated_count
                import_batch.errors = error_count
                import_batch.save()

                messages.success(request, f"Import hoàn tất: {inserted_count} mới, {updated_count} cập nhật, {error_count} lỗi.")
                return redirect('admin:students_importbatch_changelist')

            except Exception as e:
                messages.error(request, f"Lỗi đọc file: {str(e)[:250]}")
                return redirect('admin:students_student_changelist')

        context = dict(
            self.admin_site.each_context(request),
            title="📥 Upload Danh sách Sinh viên",
            batches=GraduationBatch.objects.all()
        )
        return render(request, "admin/students/import_excel.html", context)