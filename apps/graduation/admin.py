from apps.blockchain.models import IssuanceBatch, DegreeMerkleProof
from apps.workflow.services import ensure_different_actors
import uuid
import json
from django.contrib import admin, messages
from django.utils import timezone

# Sử dụng BaseRoleAdmin dùng chung đã tạo ở app core thay cho ModelAdmin mặc định
from apps.core.admin import BaseRoleAdmin 

from apps.blockchain.services import generate_canonical_hash, build_merkle_root
from apps.degrees.models import Degree
from apps.students.models import Student, ImportBatchItem
from apps.academic.models import DegreeType
from .models import GraduationBatch


@admin.register(GraduationBatch)
class GraduationBatchAdmin(BaseRoleAdmin):
    # CHỈ Cán bộ nhập liệu (Maker) và Cán bộ phê duyệt (Checker) mới được vào giao diện này
    allowed_roles = ['officer_a', 'academic_staff', 'officer_b', 'reviewer', 'approver']
    
    list_display = ['name', 'status', 'maker', 'checker', 'approved_at', 'merkle_root']
    search_fields = ['name']
    
    actions = ['submit_for_approval', 'approve_batch', 'reject_batch']

    @admin.action(description="1. Trình duyệt danh sách (Dành cho Maker)")
    def submit_for_approval(self, request, queryset):
        # --- KIỂM TRA QUYỀN ACTION CỦA TÁC NHÂN ---
        user_roles = request.user.roles.values_list('code', flat=True) if request.user.is_authenticated else []
        is_maker = request.user.is_superuser or 'officer_a' in user_roles or 'academic_staff' in user_roles
        
        if not is_maker:
            self.message_user(request, "Lỗi phân quyền: Chỉ Cán bộ nhập liệu (Maker) mới được phép Trình duyệt!", level=messages.ERROR)
            return

        for batch in queryset:
            if batch.status != 'DRAFT':
                self.message_user(request, f"Đợt '{batch.name}' không ở trạng thái Nháp!", level=messages.ERROR)
                continue
            
            # Đánh dấu người trình và đổi trạng thái
            batch.status = 'PENDING'
            batch.maker = request.user
            batch.save()
            
        self.message_user(request, "Đã trình duyệt danh sách! Chờ Cán bộ phê duyệt xử lý.", level=messages.SUCCESS)


    @admin.action(description="2. Phê duyệt & Tạo phôi Blockchain (Dành cho Checker)")
    def approve_batch(self, request, queryset):
        # --- KIỂM TRA QUYỀN ACTION CỦA TÁC NHÂN ---
        user_roles = request.user.roles.values_list('code', flat=True) if request.user.is_authenticated else []
        is_checker = request.user.is_superuser or 'officer_b' in user_roles or 'reviewer' in user_roles or 'approver' in user_roles
        
        if not is_checker:
            self.message_user(request, "Lỗi phân quyền: Chỉ Cán bộ phê duyệt (Checker) mới được thao tác nút này!", level=messages.ERROR)
            return

        default_degree_type = DegreeType.objects.first()
        
        # Bắt lỗi nếu hệ thống chưa cấu hình Loại văn bằng
        if not default_degree_type:
            self.message_user(request, "Hệ thống chưa có 'Loại văn bằng'. Vui lòng tạo ít nhất 1 loại trong Danh mục đào tạo trước khi duyệt!", level=messages.ERROR)
            return

        for batch in queryset:
            if batch.status != 'PENDING':
                self.message_user(request, f"Đợt '{batch.name}' chưa được trình duyệt!", level=messages.ERROR)
                continue
                
            try:
                # 1. Thay thế kiểm tra tay bằng hàm 4-eyes dùng chung
                ensure_different_actors(batch.maker, request.user)
                
                # --- 1. CHỐT DUYỆT ---
                batch.status = 'APPROVED'
                batch.checker = request.user
                batch.approved_at = timezone.now()
                
                # --- 2. LỌC DANH SÁCH SINH VIÊN (Truy xuất qua lịch sử Import) ---
                successful_student_codes = ImportBatchItem.objects.filter(
                    import_batch__batch=batch,
                    action__in=['INSERT', 'UPDATE']
                ).values_list('student_code', flat=True)
                
                unique_student_codes = list(set(successful_student_codes))

                students = Student.objects.filter(student_code__in=unique_student_codes)
                
                if not students.exists():
                    self.message_user(request, f"Đợt '{batch.name}' chưa có dữ liệu sinh viên hợp lệ nào được import!", level=messages.ERROR)
                    continue

                # --- 3. THUẬT TOÁN TẠO HASH & PHÔI BẰNG VÀ CHUẨN BỊ MERKLE PROOF ---
                leaves = []
                degrees_to_create = []

                for student in students:
                    degree_type = student.major.degree_type if hasattr(student.major, 'degree_type') else None
                    if not degree_type:
                        raise ValueError(f"Ngành của sinh viên {student.student_code} chưa được cấu hình Loại văn bằng.")

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
                        canonical_hash=c_hash,
                        status='PENDING'
                    ))
                
                created_degrees = Degree.objects.bulk_create(degrees_to_create)
                
                # 4. TẠO MERKLE ROOT CHO CẢ ĐỢT
                merkle_root = build_merkle_root(leaves)
                batch.merkle_root = merkle_root
                
                # 5. Tạo IssuanceBatch (Khối cấp phát chờ ký MetaMask)
                issuance_batch = IssuanceBatch.objects.create(
                    graduation_batch=batch,
                    merkle_root=merkle_root,
                    status='PENDING' 
                )

                # 6. Tạo DegreeMerkleProof cho Nghĩa xác thực
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

                # 7. CHỐT DUYỆT
                batch.save()
                    
                self.message_user(request, f"Đã duyệt đợt {batch.name}! Chuyển sang bước Ký phát hành bằng MetaMask.", level=messages.SUCCESS)

            except Exception as e:
                self.message_user(request, f"Lỗi xử lý đợt {batch.name}: {str(e)}", level=messages.ERROR)
    
    
    @admin.action(description="3. Từ chối đợt (Trả về bản nháp)")
    def reject_batch(self, request, queryset):
        for batch in queryset:
            if batch.status != 'PENDING':
                self.message_user(request, f"Đợt '{batch.name}' không ở trạng thái Chờ duyệt!", level=messages.ERROR)
                continue
            
            batch.status = 'DRAFT'
            batch.maker = None # Reset lại người trình
            # Nếu model GraduationBatch có trường note/reason, bạn lưu lý do vào đây:
            # batch.note = f"Bị từ chối bởi {request.user.username}"
            batch.save()
            
        self.message_user(request, "Đã từ chối và trả đợt về trạng thái Nháp.", level=messages.SUCCESS)