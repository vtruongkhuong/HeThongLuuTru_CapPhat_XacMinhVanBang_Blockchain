from django.contrib import admin
from django.http import HttpResponse
from django.contrib import messages
from apps.core.admin import BaseRoleAdmin
from .models import Degree
from .pdf_generator import get_degree_pdf
from .tasks import render_degree_pdfs  # Nhập Celery task đã tạo

@admin.register(Degree)
class DegreeAdmin(BaseRoleAdmin):
    # Quyền xem: Các cán bộ liên quan đến quy trình duyệt và phát hành
    allowed_roles = ['officer_a', 'officer_b', 'reviewer', 'approver', 'issuer']
    
    list_display = ['student', 'batch', 'degree_type', 'status', 'generated_at']
    list_filter = ['batch', 'status', 'degree_type']
    search_fields = ['student__full_name', 'student__student_code', 'canonical_hash']
    
    # Bổ sung action kết xuất hàng loạt vào danh sách
    actions = ['preview_pdf', 'generate_bulk_pdfs']

    @admin.action(description="Xem trước file PDF")
    def preview_pdf(self, request, queryset):
        # Lấy bản ghi đầu tiên trong các mục được chọn để xem trước
        degree = queryset.first()
        if not degree:
            self.message_user(request, "Vui lòng chọn ít nhất 1 văn bằng để xem.")
            return
            
        pdf_bytes = get_degree_pdf(degree)
        
        if pdf_bytes:
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            # 'inline' giúp trình duyệt mở file PDF thẳng trên tab mới thay vì tự động tải về
            response['Content-Disposition'] = f'inline; filename="degree_{degree.student.student_code}.pdf"'
            return response
        else:
            self.message_user(request, "Lỗi kết xuất PDF!", level='error')

    @admin.action(description="🛠 Kết xuất PDF hàng loạt (Chạy nền)")
    def generate_bulk_pdfs(self, request, queryset):
        # Lọc ra danh sách các batch_id duy nhất từ những văn bằng được chọn
        batch_ids = queryset.values_list('batch_id', flat=True).distinct()
        
        if not batch_ids:
            self.message_user(request, "Không tìm thấy đợt tốt nghiệp nào hợp lệ.", level=messages.WARNING)
            return

        # Gọi Celery task cho từng đợt
        for batch_id in batch_ids:
            # Dùng .delay() để ném task vào background queue của Celery
            try:
                render_degree_pdfs.delay(batch_id, actor_id=request.user.id)
            except Exception:
                render_degree_pdfs(batch_id, actor_id=request.user.id)
        
        # Báo cáo ngay lập tức cho người dùng trên UI (không cần chờ render xong)
        self.message_user(
            request, 
            f"🚀 Đã đưa yêu cầu kết xuất PDF của {len(batch_ids)} đợt vào hàng đợi xử lý nền. Các văn bằng hợp lệ sẽ tự động chuyển sang trạng thái GENERATED sau khi hoàn tất.",
            level=messages.SUCCESS
        )