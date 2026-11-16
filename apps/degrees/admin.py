from django.contrib import admin, messages
from django.http import HttpResponse
from django.shortcuts import render, redirect
from apps.core.admin import BaseRoleAdmin, format_crypto_hash_badge
from .models import Degree
from .pdf_generator import get_degree_pdf
from .tasks import render_degree_pdfs
from .services import submit_degree_for_approval, approve_degree
from apps.blockchain.models import IssuanceBatch
from apps.blockchain.client import BlockchainClient


@admin.register(Degree)
class DegreeAdmin(BaseRoleAdmin):
    # Quyền xem: Các cán bộ liên quan đến quy trình duyệt và phát hành
    allowed_roles = ['officer_a', 'officer_b', 'reviewer', 'approver', 'issuer']
    
    list_display = ['student', 'batch', 'degree_type', 'status', 'short_canonical_hash', 'generated_at']

    def short_canonical_hash(self, obj):
        return format_crypto_hash_badge(obj.canonical_hash, title_prefix="Mã Hash Văn Bằng (Canonical Hash)", icon="fingerprint")
    short_canonical_hash.short_description = "Mã Hash Văn Bằng"
    
    list_filter = ('batch', 'status', 'degree_type')
    list_filter_submit = True
    search_fields = ['student__full_name', 'student__student_code', 'canonical_hash']
    
    # Bổ sung các action Đơn lẻ và Hàng loạt
    actions = [
        'submit_single_for_approval',
        'approve_single_degree',
        'issue_single_metamask',
        'preview_pdf',
        'generate_bulk_pdfs'
    ]

    # --- 1. ACTION ĐƠN LẺ: TRÌNH DUYỆT (MAKER) ---
    @admin.action(description="1. [Đơn lẻ] Trình duyệt văn bằng (Maker)")
    def submit_single_for_approval(self, request, queryset):
        user_roles = request.user.roles.values_list('code', flat=True) if hasattr(request.user, 'roles') else []
        is_maker = request.user.is_superuser or 'officer_a' in user_roles or 'reviewer' in user_roles
        if not is_maker:
            self.message_user(request, "Lỗi phân quyền: Chỉ Cán bộ giáo vụ (Maker) mới có quyền trình duyệt văn bằng!", level=messages.ERROR)
            return

        success_count = 0
        for degree in queryset:
            try:
                submit_degree_for_approval(degree.id, request.user)
                success_count += 1
            except Exception as e:
                self.message_user(request, f"Không thể trình duyệt bằng của {degree.student.full_name}: {str(e)}", level=messages.WARNING)

        if success_count > 0:
            self.message_user(request, f"✅ Đã trình duyệt thành công {success_count} văn bằng. Trạng thái chuyển sang REVIEWED (Chờ lãnh đạo duyệt).", level=messages.SUCCESS)

    # --- 2. ACTION ĐƠN LẺ: PHÊ DUYỆT (CHECKER) ---
    @admin.action(description="2. [Đơn lẻ] Phê duyệt & Cấp phôi On-Chain (Checker)")
    def approve_single_degree(self, request, queryset):
        user_roles = request.user.roles.values_list('code', flat=True) if hasattr(request.user, 'roles') else []
        is_checker = request.user.is_superuser or 'officer_b' in user_roles or 'approver' in user_roles
        if not is_checker:
            self.message_user(request, "Lỗi phân quyền: Chỉ Cán bộ phê duyệt (Checker) mới có quyền phê duyệt văn bằng!", level=messages.ERROR)
            return

        success_count = 0
        for degree in queryset:
            try:
                approve_degree(degree.id, request.user)
                success_count += 1
            except Exception as e:
                self.message_user(request, f"Không thể phê duyệt bằng của {degree.student.full_name}: {str(e)}", level=messages.ERROR)

        if success_count > 0:
            self.message_user(request, f"🚀 Đã phê duyệt và tạo phôi thành công cho {success_count} văn bằng! Đã tự động sinh Canonical Hash (kèm GPA) và file PDF.", level=messages.SUCCESS)

    # --- 3. ACTION ĐƠN LẺ: KÝ PHÁT HÀNH METAMASK (ISSUER) ---
    @admin.action(description="3. [Đơn lẻ] Ký phát hành qua MetaMask (Issuer)")
    def issue_single_metamask(self, request, queryset):
        user_roles = request.user.roles.values_list('code', flat=True) if hasattr(request.user, 'roles') else []
        is_issuer = request.user.is_superuser or 'issuer' in user_roles
        if not is_issuer:
            self.message_user(request, "Lỗi phân quyền: Chỉ Cán bộ phát hành (Issuer) mới có quyền ký giao dịch Blockchain!", level=messages.ERROR)
            return

        if queryset.count() != 1:
            self.message_user(request, "Vui lòng chỉ chọn ĐÚNG 1 văn bằng để phát hành đơn lẻ qua MetaMask!", level=messages.ERROR)
            return

        degree = queryset.first()
        if degree.status not in ('APPROVED', 'GENERATED'):
            self.message_user(request, f"Văn bằng phải ở trạng thái ĐÃ DUYỆT (APPROVED). Hiện tại đang là: {degree.get_status_display()}", level=messages.ERROR)
            return

        try:
            client = BlockchainClient()
            contract_address = client.contract_address

            # Đảm bảo mã hash đã có
            if not degree.canonical_hash:
                from .canonicalizer import degree_leaf_hash
                degree.canonical_hash = degree_leaf_hash(degree)
                degree.save(update_fields=['canonical_hash'])

            # Đặt tên định danh cho đợt đơn lẻ này
            batch_name = f"{degree.batch.name} - {degree.student.student_code}"
            batch_id_hex = client.batch_id_of(batch_name)

            # Chống phát hành trùng trên chuỗi
            existing = client.get_batch(batch_id_hex)
            if existing and existing.get('root') and existing['root'] not in ('', '0' * 64):
                self.message_user(request, f"Cảnh báo: Văn bằng này đã được phát hành trên Blockchain Sepolia (batchId: {batch_id_hex[:10]}...)!", level=messages.WARNING)
                return

            # Lấy hoặc tạo IssuanceBatch
            issuance_batch, _ = IssuanceBatch.objects.get_or_create(
                graduation_batch=degree.batch,
                merkle_root=degree.canonical_hash,
                defaults={'status': 'PENDING'}
            )

            tx_data = client.build_issue_tx_data(
                batch_name=batch_name,
                merkle_root_hex=degree.canonical_hash,
                count=1
            )

            context = {
                'batch': issuance_batch,
                'contract_address': contract_address,
                'tx_data': tx_data,
                'is_single': True,
                'degree': degree,
            }
            return render(request, 'admin/blockchain/issuancebatch/issue_metamask.html', context)

        except Exception as e:
            self.message_user(request, f"Lỗi khởi tạo giao dịch Web3 đơn lẻ: {str(e)}", level=messages.ERROR)

    # --- 4. ACTION XEM TRƯỚC PDF ---
    @admin.action(description="Xem trước file PDF")
    def preview_pdf(self, request, queryset):
        degree = queryset.first()
        if not degree:
            self.message_user(request, "Vui lòng chọn ít nhất 1 văn bằng để xem.")
            return
            
        pdf_bytes = get_degree_pdf(degree)
        if pdf_bytes:
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="degree_{degree.student.student_code}.pdf"'
            return response
        else:
            self.message_user(request, "Lỗi kết xuất PDF!", level='error')

    # --- 5. ACTION KẾT XUẤT HÀNG LOẠT ---
    @admin.action(description="🛠 Kết xuất PDF hàng loạt (Chạy nền)")
    def generate_bulk_pdfs(self, request, queryset):
        batch_ids = queryset.values_list('batch_id', flat=True).distinct()
        if not batch_ids:
            self.message_user(request, "Không tìm thấy đợt tốt nghiệp nào hợp lệ.", level=messages.WARNING)
            return

        for batch_id in batch_ids:
            try:
                render_degree_pdfs.delay(batch_id, actor_id=request.user.id)
            except Exception:
                render_degree_pdfs(batch_id, actor_id=request.user.id)
        
        self.message_user(
            request, 
            f"🚀 Đã đưa yêu cầu kết xuất PDF của {len(batch_ids)} đợt vào hàng đợi xử lý nền.",
            level=messages.SUCCESS
        )
