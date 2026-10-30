import uuid
import json
from django.urls import path
from django.utils.html import format_html
from django.shortcuts import render
from django.contrib import admin, messages
from django.utils import timezone
from apps.students.utils import get_classification_from_gpa
from apps.blockchain.models import IssuanceBatch, DegreeMerkleProof
from apps.workflow.services import ensure_different_actors
from apps.core.admin import BaseRoleAdmin, format_crypto_hash_badge 

from apps.blockchain.services import get_merkle_proof, build_merkle_root
from apps.degrees.canonicalizer import canonical_hash, HASH_VERSION
from apps.degrees.models import Degree
from apps.students.models import Student, ImportBatchItem
from .models import GraduationBatch

from apps.degrees.tasks import render_degree_pdfs

@admin.register(GraduationBatch)
class GraduationBatchAdmin(BaseRoleAdmin):
    allowed_roles = ['officer_a', 'officer_b']
    
    # --- THAY ĐỔI 1: CẬP NHẬT MẢNG list_display ---
    list_display = ['name', 'view_students_link', 'status', 'maker', 'checker', 'approved_at', 'short_merkle_root']
    list_filter = ('status', 'degree_type')
    list_filter_submit = True
    search_fields = ['name']
    actions = ['submit_for_approval', 'approve_batch', 'reject_batch', 'generate_batch_pdfs']

    # Khai báo nút này để hiển thị trong trang CHỈNH SỬA CHI TIẾT
    readonly_fields = ['view_students_btn']

    def view_students_btn(self, obj):
        if obj.pk:
            url = f"/admin/graduation/graduationbatch/{obj.pk}/students/"
            return format_html(
                '<a href="{}" target="_blank" class="apple-action-btn-primary" style="padding: 9px 18px; font-size: 13px;">'
                '<span class="material-symbols-outlined" style="font-size:18px;">groups</span>'
                '<span>Nhấn vào đây để xem Danh sách Sinh viên</span>'
                '</a>',
                url
            )
        return "Hãy lưu đợt này lại trước khi xem danh sách"
    view_students_btn.short_description = "Tra cứu Danh sách"

    # --- THAY ĐỔI 2: THÊM 2 HÀM XỬ LÝ GIAO DIỆN BẢNG BÊN NGOÀI ---
    
    # Hàm 2.1: Tạo nút xem danh sách nhỏ gọn
    def view_students_link(self, obj):
        if obj.pk:
            url = f"/admin/graduation/graduationbatch/{obj.pk}/students/"
            return format_html(
                '<a href="{}" target="_blank" class="apple-view-list-btn">'
                '<span class="material-symbols-outlined" style="font-size:14px;">groups</span>'
                '<span>Xem DS</span>'
                '</a>',
                url
            )
        return "-"
    view_students_link.short_description = "Danh sách"

    # --- HÀM 2.2: RÚT GỌN VÀ THÊM TÍNH NĂNG CLICK TO COPY CHO MERKLE ROOT ---
    def short_merkle_root(self, obj):
        return format_crypto_hash_badge(obj.merkle_root, title_prefix="Mã Merkle Root", icon="tag")
    short_merkle_root.short_description = "Mã Merkle Root"


    # --- 3. URL VÀ HÀM XỬ LÝ TRANG DANH SÁCH SINH VIÊN ---
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:object_id>/students/', self.admin_site.admin_view(self.view_students_list), name='batch_students_list'),
        ]
        return custom_urls + urls

    def view_students_list(self, request, object_id):
        batch = self.get_object(request, object_id)
        
        # THÊM .order_by() ĐỂ SẮP XẾP THEO LOẠI BẰNG RỒI ĐẾN MÃ SINH VIÊN
        degrees = Degree.objects.filter(batch=batch).select_related('student__major', 'degree_type').order_by('degree_type__name', 'student__student_code')
        
        students_data = []
        if degrees.exists():
            for d in degrees:
                # Làm ngắn mã hash
                short_hash = f"{d.canonical_hash[:6]}...{d.canonical_hash[-6:]}" if (d.canonical_hash and len(d.canonical_hash) > 15) else (d.canonical_hash or "Chờ băm")
                
                students_data.append({
                    'code': d.student.student_code,
                    'name': d.student.full_name,
                    'major': str(d.student.major) if d.student.major else "N/A",
                    'degree_type': str(d.degree_type) if d.degree_type else "N/A",
                    'hash': short_hash,
                    'full_hash': d.canonical_hash or "Chưa tạo mã",
                    'status': d.get_status_display()
                })
        else:
            # Nếu đang ở bản nháp, lấy từ bảng Import ra
            successful_student_codes = ImportBatchItem.objects.filter(
                import_batch__batch=batch,
                action__in=['INSERT', 'UPDATE']
            ).values_list('student_code', flat=True)
            
            unique_student_codes = list(set(successful_student_codes))
            
            # SẮP XẾP LUÔN CHO BẢN NHÁP
            students = Student.objects.filter(student_code__in=unique_student_codes).select_related('major__degree_type').order_by('major__degree_type__name', 'student_code')

            for s in students:
                dt = batch.degree_type or (s.major.degree_type if (hasattr(s, 'major') and s.major) else None)
                
                students_data.append({
                    'code': s.student_code,
                    'name': s.full_name,
                    'major': str(s.major) if (hasattr(s, 'major') and s.major) else "N/A",
                    'degree_type': str(dt) if dt else "Chưa gán",
                    'hash': "-",
                    'full_hash': "Sẽ tạo khi duyệt",
                    'status': 'Bản nháp (Chờ duyệt)'
                })

        context = {
            'batch': batch,
            'students': students_data,
            'total': len(students_data),
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request, batch),
        }
        return render(request, 'admin/graduation/graduationbatch/students_list.html', context)


    # --- 4. CÁC ACTIONS QUY TRÌNH KÝ DUYỆT ---
    @admin.action(description="1. Trình duyệt danh sách (Dành cho Maker)")
    def submit_for_approval(self, request, queryset):
        user_roles = request.user.roles.values_list('code', flat=True) if hasattr(request.user, 'roles') else []
        is_maker = request.user.is_superuser or 'officer_a' in user_roles
        
        if not is_maker:
            self.message_user(request, "Lỗi phân quyền: Chỉ Cán bộ nhập liệu (Maker - officer_a) mới được phép Trình duyệt!", level=messages.ERROR)
            return

        for batch in queryset:
            if batch.status != 'DRAFT':
                self.message_user(request, f"Đợt '{batch.name}' không ở trạng thái Nháp!", level=messages.ERROR)
                continue
            
            batch.status = 'PENDING'
            batch.maker = request.user
            batch.save()
            
        self.message_user(request, "Đã trình duyệt danh sách! Chờ Cán bộ phê duyệt xử lý.", level=messages.SUCCESS)

    @admin.action(description="2. Phê duyệt & Tạo phôi Blockchain (Dành cho Checker)")
    def approve_batch(self, request, queryset):
        user_roles = request.user.roles.values_list('code', flat=True) if hasattr(request.user, 'roles') else []
        is_checker = request.user.is_superuser or 'officer_b' in user_roles
        
        if not is_checker:
            self.message_user(request, "Lỗi phân quyền: Chỉ Cán bộ phê duyệt (Checker - officer_b) mới được thao tác nút này!", level=messages.ERROR)
            return

        for batch in queryset:
            if batch.status != 'PENDING':
                self.message_user(request, f"Đợt '{batch.name}' chưa được trình duyệt!", level=messages.ERROR)
                continue
                
            try:
                if not request.user.is_superuser:
                    ensure_different_actors(batch.maker, request.user)
                
                successful_student_codes = ImportBatchItem.objects.filter(
                    import_batch__batch=batch,
                    action__in=['INSERT', 'UPDATE']
                ).values_list('student_code', flat=True)
                
                unique_student_codes = list(set(successful_student_codes))
                students = Student.objects.filter(student_code__in=unique_student_codes).select_related('major__degree_type')
                
                if not students.exists():
                    self.message_user(request, f"Đợt '{batch.name}' chưa có dữ liệu sinh viên hợp lệ nào được import!", level=messages.ERROR)
                    continue
                
                students_missing_type = []
                for s in students:
                    dt = batch.degree_type or (s.major.degree_type if s.major else None)
                    if not dt:
                        students_missing_type.append(f"{s.student_code} ({s.full_name})")
                if students_missing_type:
                    missing_str = ", ".join(students_missing_type[:5])
                    more = f" và {len(students_missing_type) - 5} sinh viên khác" if len(students_missing_type) > 5 else ""
                    self.message_user(
                        request,
                        f"Không thể phê duyệt! Các sinh viên sau chưa có Loại văn bằng theo ngành: {missing_str}{more}. "
                        f"Vui lòng cấu hình Loại văn bằng cho Đợt này hoặc trong Danh mục Ngành.",
                        level=messages.ERROR
                    )
                    continue
                
                batch.status = 'APPROVED'
                batch.checker = request.user
                batch.approved_at = timezone.now()
                leaves = []
                degrees_to_create = []
                issue_date = timezone.now().date()

                from apps.academic.models import DegreeType
                for student in students:
                    # Ưu tiên 1: Loại bằng/chứng chỉ được chọn trong file Excel import (H5)
                    dt_code = None
                    last_item = ImportBatchItem.objects.filter(import_batch__batch=batch, student_code=student.student_code).order_by('-id').first()
                    if last_item and isinstance(last_item.new_value, dict):
                        dt_code = last_item.new_value.get('degree_type')

                    degree_type = None
                    if dt_code:
                        degree_type = DegreeType.objects.filter(code__iexact=dt_code).first()
                        if not degree_type and dt_code.upper() in ['CN', 'KS', 'THVP', 'CNTT']:
                            degree_type = DegreeType.objects.filter(code__icontains=dt_code).first()

                    # Ưu tiên 2 & 3: Đợt tốt nghiệp hoặc Ngành học
                    if not degree_type:
                        degree_type = batch.degree_type or (student.major.degree_type if student.major else None)
                    pub_id = uuid.uuid4()
                    classification = get_classification_from_gpa(student.gpa_score) or ""
                    
                    leaf_data = {
                        "hash_version": HASH_VERSION,
                        "credential_public_id": str(pub_id),
                        "student_code": student.student_code,
                        "full_name": student.full_name,
                        "major_code": student.major.code if student.major else "",
                        "degree_type_code": degree_type.code,
                        "batch_name": batch.name,
                        "classification": classification,
                        "issue_date": str(issue_date),
                    }
                    c_hash = canonical_hash(leaf_data)
                    leaves.append(c_hash)
                    
                    # K9: approve_batch chỉ đặt Degree sang APPROVED
                    degrees_to_create.append(Degree(
                        student=student,
                        batch=batch,
                        degree_type=degree_type,
                        credential_public_id=pub_id,
                        classification=classification,
                        issue_date=issue_date,
                        canonical_hash=c_hash,
                        status='APPROVED',
                        pdf_path='',
                        template_version='1.0',
                        credential_version='1.0',
                        reviewed_by=batch.maker,
                        reviewed_at=batch.approved_at,
                        approved_by=request.user,
                        approved_at=timezone.now()
                    ))
                
                created_degrees = Degree.objects.bulk_create(degrees_to_create)
                
                merkle_root = build_merkle_root(leaves)
                batch.merkle_root = merkle_root
                
                issuance_batch = IssuanceBatch.objects.create(
                    graduation_batch=batch,
                    merkle_root=merkle_root,
                    status='PENDING'
                )

                proofs_to_create = []
                for index, (degree, leaf_hash) in enumerate(zip(created_degrees, leaves)):
                    real_proof = get_merkle_proof(leaves, index)
                    proofs_to_create.append(DegreeMerkleProof(
                        degree=degree,
                        issuance_batch=issuance_batch,
                        leaf_hash=leaf_hash,
                        leaf_index=index, 
                        proof_path=real_proof
                    ))
                DegreeMerkleProof.objects.bulk_create(proofs_to_create)

                batch.save()
                try:
                    from apps.audit.services import log_action
                    log_action(
                        actor=request.user,
                        action='APPROVE_BATCH',
                        entity_type='GraduationBatch',
                        entity_id=str(batch.id),
                        new={'status': 'APPROVED', 'merkle_root': merkle_root, 'total_degrees': len(created_degrees)},
                        request=request
                    )
                except Exception:
                    pass
                self.message_user(request, f"Đã duyệt đợt {batch.name}! Chuyển sang bước Ký phát hành bằng MetaMask.", level=messages.SUCCESS)

            except Exception as e:
                self.message_user(request, f"Lỗi xử lý đợt {batch.name}: {str(e)}", level=messages.ERROR)
    
    @admin.action(description="3. Từ chối đợt (Trả về bản nháp)")
    def reject_batch(self, request, queryset):
        user_roles = request.user.roles.values_list('code', flat=True) if hasattr(request.user, 'roles') else []
        is_checker = request.user.is_superuser or 'officer_b' in user_roles
        
        if not is_checker:
            self.message_user(request, "Chỉ Cán bộ phê duyệt mới được từ chối đợt!", level=messages.ERROR)
            return

        for batch in queryset:
            if batch.status != 'PENDING':
                self.message_user(request, f"Đợt '{batch.name}' không ở trạng thái Chờ duyệt!", level=messages.ERROR)
                continue
            
            batch.status = 'DRAFT'
            batch.maker = None 
            batch.save()
            
        self.message_user(request, "Đã từ chối và trả đợt về trạng thái Nháp.", level=messages.SUCCESS)

    @admin.action(description="🛠 4. Kết xuất PDF hàng loạt (Chạy nền)")
    def generate_batch_pdfs(self, request, queryset):
        # Lớp bảo mật: Chỉ những cán bộ có quyền mới được bấm
        user_roles = request.user.roles.values_list('code', flat=True) if hasattr(request.user, 'roles') else []
        is_authorized = request.user.is_superuser or 'officer_b' in user_roles or 'officer_a' in user_roles
        
        if not is_authorized:
            self.message_user(request, "Bạn không có quyền thực hiện kết xuất PDF!", level=messages.ERROR)
            return

        count = 0
        for batch in queryset:
            # Chỉ cho phép kết xuất khi đợt đã được duyệt (APPROVED) và đã sinh Degree
            if batch.status != 'APPROVED':
                self.message_user(request, f"Đợt '{batch.name}' phải ở trạng thái ĐÃ DUYỆT (APPROVED) mới có dữ liệu Văn bằng để xuất PDF.", level=messages.ERROR)
                continue
            
            # Gửi ID của đợt tốt nghiệp vào hàng đợi Celery
            try:
                render_degree_pdfs.delay(batch.id, actor_id=request.user.id)
            except Exception:
                render_degree_pdfs(batch.id, actor_id=request.user.id)
            count += 1
            
        if count > 0:
            self.message_user(request, f"🚀 Đã đẩy {count} đợt vào hàng đợi. Hệ thống đang tự động kết xuất PDF ở chế độ chạy nền.", level=messages.SUCCESS)