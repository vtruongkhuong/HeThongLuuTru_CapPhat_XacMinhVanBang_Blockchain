from django.contrib import admin, messages
from django.utils import timezone
from unfold.admin import ModelAdmin

from .models import GraduationBatch
from apps.blockchain.services import generate_canonical_hash, build_merkle_root
from apps.degrees.models import Degree
from apps.students.models import Student 
from apps.academic.models import DegreeType

@admin.register(GraduationBatch)
class GraduationBatchAdmin(ModelAdmin):
    # Đã thêm merkle_root vào list_display để xem mã Hash ngay ngoài bảng
    list_display = ['name', 'status', 'maker', 'checker', 'approved_at', 'merkle_root']
    search_fields = ['name']
    
    actions = ['submit_for_approval', 'approve_batch']

    @admin.action(description="1. Trình duyệt danh sách (Dành cho Maker)")
    def submit_for_approval(self, request, queryset):
        for batch in queryset:
            if batch.status != 'DRAFT':
                self.message_user(request, f"Đợt '{batch.name}' không ở trạng thái Nháp!", level=messages.ERROR)
                continue
            
            # Đánh dấu người trình
            batch.status = 'PENDING'
            batch.maker = request.user
            batch.save()
            
        self.message_user(request, "Đã trình duyệt danh sách! Chờ Lãnh đạo phê duyệt.", level=messages.SUCCESS)

    @admin.action(description="2. Phê duyệt & Tạo phôi Blockchain (Dành cho Checker)")
    def approve_batch(self, request, queryset):
        default_degree_type = DegreeType.objects.first()
        
        # 1. Bắt lỗi sập Database nếu chưa có Loại văn bằng
        if not default_degree_type:
            self.message_user(request, "Hệ thống chưa có 'Loại văn bằng'. Vui lòng tạo ít nhất 1 loại trong Danh mục đào tạo trước khi duyệt!", level=messages.ERROR)
            return

        for batch in queryset:
            if batch.status != 'PENDING':
                self.message_user(request, f"Đợt '{batch.name}' chưa được trình duyệt!", level=messages.ERROR)
                continue
            
            # 2. Đổi câu cảnh báo cho chuyên nghiệp, bỏ chữ "Luật 4 mắt"
            if batch.maker == request.user:
                self.message_user(
                    request, 
                    f"Lỗi phân quyền: Tài khoản '{request.user.username}' không được phép tự phê duyệt danh sách do chính mình lập.", 
                    level=messages.ERROR
                )
                continue
            
            # --- 1. CHỐT DUYỆT (PASS QUA LUẬT 4 MẮT) ---
            batch.status = 'APPROVED'
            batch.checker = request.user
            batch.approved_at = timezone.now()
            
            # --- 2. THUẬT TOÁN TẠO HASH & PHÔI BẰNG ---
            students = Student.objects.all() 
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
            
            # Đẩy toàn bộ phôi bằng vào DB cùng lúc cho mượt
            if degrees_to_create:
                Degree.objects.bulk_create(degrees_to_create)
            
            # --- 3. TẠO MERKLE ROOT CHO CẢ ĐỢT ---
            batch.merkle_root = build_merkle_root(hash_list)
            batch.save()
            
        self.message_user(request, "Đã duyệt và tạo phôi Blockchain thành công!", level=messages.SUCCESS)