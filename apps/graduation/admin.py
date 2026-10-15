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
from apps.core.admin import BaseRoleAdmin 

from apps.blockchain.services import generate_canonical_hash, build_merkle_root
from apps.degrees.models import Degree
from apps.students.models import Student, ImportBatchItem
from apps.academic.models import DegreeType
from .models import GraduationBatch

@admin.register(GraduationBatch)
class GraduationBatchAdmin(BaseRoleAdmin):
    allowed_roles = ['officer_a', 'officer_b']
    
    # --- THAY ĐỔI 1: CẬP NHẬT MẢNG list_display ---
    list_display = ['name', 'view_students_link', 'status', 'maker', 'checker', 'approved_at', 'short_merkle_root']
    
    search_fields = ['name']
    actions = ['submit_for_approval', 'approve_batch', 'reject_batch']

    # Khai báo nút này để hiển thị trong trang CHỈNH SỬA CHI TIẾT (Trang bên trong)
    readonly_fields = ['view_students_btn']

    def view_students_btn(self, obj):
        if obj.pk:
            url = f"/admin/graduation/graduationbatch/{obj.pk}/students/"
            return format_html(
                '<a href="{}" target="_blank" style="background: #2563eb; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 14px; display: inline-block;">👀 Nhấn vào đây để xem Danh sách Sinh viên</a>',
                url
            )
        return "Hãy lưu đợt này lại trước khi xem danh sách"
    view_students_btn.short_description = "Tra cứu Danh sách"

    # --- THAY ĐỔI 2: THÊM 2 HÀM XỬ LÝ GIAO DIỆN BẢNG BÊN NGOÀI ---
    
    # Hàm 2.1: Tạo nút bấm nhỏ gọn nằm kế tên đợt ở bảng danh sách ngoài
    def view_students_link(self, obj):
        if obj.pk:
            url = f"/admin/graduation/graduationbatch/{obj.pk}/students/"
            return format_html(
                '<a href="{}" target="_blank" style="background: #10b981; color: white; padding: 4px 8px; border-radius: 4px; text-decoration: none; font-size: 12px; font-weight: bold; white-space: nowrap;">👥 Xem DS</a>',
                url
            )
        return "-"
    view_students_link.short_description = "Danh sách"

    # --- HÀM 2.2: RÚT GỌN VÀ THÊM TÍNH NĂNG CLICK TO COPY CHO MERKLE ROOT ---
    def short_merkle_root(self, obj):
        if obj.merkle_root:
            full_hash = str(obj.merkle_root)
            if len(full_hash) > 20:
                short_hash = f"{full_hash[:8]}...{full_hash[-8:]}"
                
                # Gom chung JS vào 1 dòng gọn gàng, đổi màu nền khi click để báo hiệu
                inline_js = f"navigator.clipboard.writeText('{full_hash}'); this.innerHTML='✅ Đã copy!'; setTimeout(()=>{{this.innerHTML='{short_hash}';}}, 1500);"
                
                return format_html(
                    '<span title="Nhấn để copy: {}" '
                    'onclick="{}" '
                    'style="cursor: pointer; font-family: monospace; background: #f3f4f6; padding: 4px 8px; border-radius: 4px; border: 1px solid #e5e7eb; display: inline-block; min-width: 140px; text-align: center;">{}</span>',
                    full_hash, inline_js, short_hash
                )
            return full_hash
        return "-"
    short_merkle_root.short_description = "Mã Merkle Root"


    # --- 3. URL VÀ HÀM XỬ LÝ TRANG DANH SÁCH SINH VIÊN (Giữ nguyên) ---
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
            
            default_degree_type = DegreeType.objects.first()

            for s in students:
                dt = (s.major.degree_type if (hasattr(s, 'major') and s.major) else None) or default_degree_type
                
                students_data.append({
                    'code': s.student_code,
                    'name': s.full_name,
                    'major': str(s.major) if (hasattr(s, 'major') and s.major) else "N/A",
                    'degree_type': str(dt) if dt else "N/A",
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


    # --- 4. CÁC ACTIONS QUY TRÌNH KÝ DUYỆT (Giữ nguyên) ---
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

        default_degree_type = DegreeType.objects.first()
        if not default_degree_type:
            self.message_user(request, "Hệ thống chưa có 'Loại văn bằng'. Vui lòng tạo ít nhất 1 loại trong Danh mục đào tạo trước khi duyệt!", level=messages.ERROR)
            return

        for batch in queryset:
            if batch.status != 'PENDING':
                self.message_user(request, f"Đợt '{batch.name}' chưa được trình duyệt!", level=messages.ERROR)
                continue
                
            try:
                ensure_different_actors(batch.maker, request.user)
                
                batch.status = 'APPROVED'
                batch.checker = request.user
                batch.approved_at = timezone.now()
                
                successful_student_codes = ImportBatchItem.objects.filter(
                    import_batch__batch=batch,
                    action__in=['INSERT', 'UPDATE']
                ).values_list('student_code', flat=True)
                
                unique_student_codes = list(set(successful_student_codes))
                students = Student.objects.filter(student_code__in=unique_student_codes).select_related('major__degree_type')
                
                if not students.exists():
                    self.message_user(request, f"Đợt '{batch.name}' chưa có dữ liệu sinh viên hợp lệ nào được import!", level=messages.ERROR)
                    continue

                leaves = []
                degrees_to_create = []

                for student in students:
                    degree_type = (student.major.degree_type if student.major else None) or default_degree_type
                    degree_data = {
                        "student_code": student.student_code,
                        "full_name": student.full_name,
                        "major": student.major.code if student.major else "",
                        "batch_name": batch.name,
                        "timestamp": str(uuid.uuid4())
                    }
                    c_hash = generate_canonical_hash(degree_data)
                    leaves.append(c_hash)
                    
                    degrees_to_create.append(Degree(
                        student=student,
                        batch=batch,
                        degree_type=degree_type,
                        classification=get_classification_from_gpa(student.gpa_score),
                        issue_date=timezone.now().date(),
                        canonical_hash=c_hash,
                        status='ISSUANCE_PENDING',
                        pdf_path='',
                        template_version='1.0',
                        credential_version='1.0',
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
                    proofs_to_create.append(DegreeMerkleProof(
                        degree=degree,
                        issuance_batch=issuance_batch,
                        leaf_hash=leaf_hash,
                        leaf_index=index, 
                        proof_path=json.dumps([])
                    ))
                DegreeMerkleProof.objects.bulk_create(proofs_to_create)

                batch.save()
                self.message_user(request, f"Đã duyệt đợt {batch.name}! Chuyển sang bước Ký phát hành bằng MetaMask.", level=messages.SUCCESS)

            except Exception as e:
                self.message_user(request, f"Lỗi xử lý đợt {batch.name}: {str(e)}", level=messages.ERROR)
    
    @admin.action(description="3. Từ chối đợt (Trả về bản nháp)")
    def reject_batch(self, request, queryset):
        user_roles = request.user.roles.values_list('code', flat=True) if hasattr(request.user, 'roles') else []
        is_checker = request.user.is_superuser or 'officer_b' in user_roles
        
        if not is_checker:
            self.message_user(request, "Lỗi phân quyền: Chỉ Cán bộ phê duyệt mới được từ chối đợt!", level=messages.ERROR)
            return

        for batch in queryset:
            if batch.status != 'PENDING':
                self.message_user(request, f"Đợt '{batch.name}' không ở trạng thái Chờ duyệt!", level=messages.ERROR)
                continue
            
            batch.status = 'DRAFT'
            batch.maker = None 
            batch.save()
            
        self.message_user(request, "Đã từ chối và trả đợt về trạng thái Nháp.", level=messages.SUCCESS)