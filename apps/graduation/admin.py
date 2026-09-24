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
    
    actions = ['submit_for_approval', 'approve_batch']

    @admin.action(description="1. Trình duyệt danh sách (Dành cho Maker)")
    def submit_for_approval(self, request, queryset):
        # --- KIỂM TRA QUYỀN ACTION CỦA TÁC NHÂN ---
        user_roles = request.user.roles.values_list('code', flat=True)
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
        user_roles = request.user.roles.values_list('code', flat=True)
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
            
            # Kiểm tra Luật 4 mắt: Người duyệt không được trùng với người trình
            if batch.maker == request.user:
                self.message_user(
                    request, 
                    f"Lỗi phân quyền: Tài khoản '{request.user.username}' không được phép tự phê duyệt danh sách do chính mình lập.", 
                    level=messages.ERROR
                )
                continue
            
            # --- 1. CHỐT DUYỆT ---
            batch.status = 'APPROVED'
            batch.checker = request.user
            batch.approved_at = timezone.now()
            
            # --- 2. LỌC DANH SÁCH SINH VIÊN (Truy xuất qua lịch sử Import) ---
            # Quét tìm các mã sinh viên đã được Import thành công (INSERT hoặc UPDATE) vào đợt tốt nghiệp này
            successful_student_codes = ImportBatchItem.objects.filter(
                import_batch__batch=batch,
                action__in=['INSERT', 'UPDATE']
            ).values_list('student_code', flat=True)
            
            # Loại bỏ các mã trùng lặp (phòng trường hợp import đè nhiều lần)
            unique_student_codes = list(set(successful_student_codes))

            # Truy xuất object Sinh viên thực tế dựa trên các mã vừa lọc được
            students = Student.objects.filter(student_code__in=unique_student_codes)
            
            if not students.exists():
                self.message_user(request, f"Đợt '{batch.name}' chưa có dữ liệu sinh viên hợp lệ nào được import!", level=messages.ERROR)
                continue

            # --- 3. THUẬT TOÁN TẠO HASH & PHÔI BẰNG ---
            hash_list = []
            degrees_to_create = []

            for student in students:
                # Trích xuất dữ liệu để băm
                degree_data = {
                    "student_code": student.student_code,
                    "full_name": student.full_name,
                    "major": student.major.code if student.major else "",
                    "batch_name": batch.name
                }
                
                # Gọi app blockchain tạo mã băm cho từng người
                c_hash = generate_canonical_hash(degree_data)
                hash_list.append(c_hash)
                
                # Gói thành Phôi bằng mới
                degrees_to_create.append(Degree(
                    student=student,
                    batch=batch,
                    degree_type=default_degree_type,
                    canonical_hash=c_hash,
                    status='GENERATED'
                ))
            
            # Đẩy toàn bộ phôi bằng vào DB cùng lúc cho tối ưu hiệu suất
            if degrees_to_create:
                Degree.objects.bulk_create(degrees_to_create)
            
            # --- 4. TẠO MERKLE ROOT CHO CẢ ĐỢT ---
            batch.merkle_root = build_merkle_root(hash_list)
            batch.save()
            
        self.message_user(request, "Đã duyệt đợt tốt nghiệp và tạo phôi Blockchain thành công!", level=messages.SUCCESS)