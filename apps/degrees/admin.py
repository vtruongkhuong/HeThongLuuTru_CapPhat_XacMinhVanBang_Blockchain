from django.contrib import admin, messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import path
from django.utils.html import format_html
from unfold.decorators import action
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
    
    list_display = ['student', 'batch', 'degree_type', 'status', 'short_canonical_hash', 'ipfs_badge', 'generated_at']
    
    list_select_related = ['student', 'batch', 'degree_type']   
    list_per_page = 25                                       
    autocomplete_fields = ['student', 'batch', 'supersedes']

    def short_canonical_hash(self, obj):
        return format_crypto_hash_badge(obj.canonical_hash, title_prefix="Mã Hash Văn Bằng (Canonical Hash)", icon="fingerprint")
    short_canonical_hash.short_description = "Mã Hash Văn Bằng"

    def ipfs_badge(self, obj):
        if obj.ipfs_cid:
            url = f"/blockchain/ipfs/{obj.ipfs_cid}/"
            return format_html(
                '<a href="{}" target="_blank" class="apple-hash-pill" style="color: #0d9488; background: #f0fdfa; border: 1px solid #99f6e4; font-size: 11px; padding: 3px 8px; border-radius: 9999px; text-decoration: none; display: inline-flex; align-items: center; gap: 4px;" title="Mở file trên IPFS: {}">'
                '<span class="material-symbols-outlined" style="font-size: 13px;">cloud_done</span>'
                '<span>IPFS: {}...{}</span>'
                '</a>',
                url, obj.ipfs_cid, obj.ipfs_cid[:4], obj.ipfs_cid[-4:]
            )
        return "-"
    ipfs_badge.short_description = "Lưu trữ IPFS"
    
    list_filter = ('batch', 'status', 'degree_type')
    list_filter_submit = True
    search_fields = ['student__full_name', 'student__student_code', 'canonical_hash']
    
    # Nút bấm hành động trên thanh công cụ Unfold Admin
    actions_list = ["create_single_degree_button"]

    @action(description="➕ Cấp bằng đơn lẻ")
    def create_single_degree_button(self, request):
        return redirect('admin:degrees_create_single')

    # Bổ sung các action Đơn lẻ và Hàng loạt
    actions = [
        'submit_single_for_approval',
        'approve_single_degree',
        'issue_single_metamask',
        'send_congratulation_email_action',
        'export_selected_so_goc_excel',
        'export_selected_so_goc_pdf',
        'preview_pdf',
        'generate_bulk_pdfs',
        'reset_to_draft',
        'sync_blockchain_status',
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
        if degree.status not in ('APPROVED', 'GENERATED', 'ISSUANCE_PENDING'):
            self.message_user(request, f"Văn bằng phải ở trạng thái ĐÃ DUYỆT (APPROVED) hoặc CHỜ PHÁT HÀNH. Hiện tại đang là: {degree.get_status_display()}", level=messages.ERROR)
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

    # --- 6. ACTION ADMIN: RESET VỀ NHÁP ĐỂ TEST LẠI ---
    @admin.action(description="🔄 [Admin] Trả văn bằng về trạng thái Nháp (DRAFT) để test lại")
    def reset_to_draft(self, request, queryset):
        user_roles = request.user.roles.values_list('code', flat=True) if hasattr(request.user, 'roles') else []
        is_admin = request.user.is_superuser or 'admin' in user_roles
        if not is_admin:
            self.message_user(request, "Lỗi phân quyền: Chỉ Quản trị viên (Admin) mới có quyền reset trạng thái văn bằng!", level=messages.ERROR)
            return

        count = queryset.update(status='DRAFT')
        self.message_user(request, f"✅ Đã reset {count} văn bằng về trạng thái Nháp (DRAFT). Bây giờ bạn có thể test lại từ Bước 1.", level=messages.SUCCESS)

    # --- 7. ACTION ĐỒNG BỘ TRẠNG THÁI ON-CHAIN ---
    @admin.action(description="🔄 Đồng bộ trạng thái On-Chain từ Sepolia")
    def sync_blockchain_status(self, request, queryset):
        from apps.blockchain.models import BlockchainTransaction
        from apps.blockchain.tasks import sync_transaction
        count = 0
        for degree in queryset:
            tx = BlockchainTransaction.objects.filter(
                Q(degree=degree) | Q(issuance_batch__graduation_batch=degree.batch)
            ).order_by('-id').first()
            if tx and tx.tx_hash:
                try:
                    sync_transaction(tx.tx_hash)
                    count += 1
                except Exception as e:
                    self.message_user(request, f"Không thể đồng bộ {degree.student.student_code}: {e}", level=messages.WARNING)
        self.message_user(request, f"🚀 Đã hoàn tất đồng bộ dữ liệu On-Chain cho {count} văn bằng.", level=messages.SUCCESS)

    # --- 8. ACTION GỬI EMAIL CHÚC MỪNG TỰ ĐỘNG BẰNG CELERY (KÈM PDF & QR CODE) ---
    @admin.action(description="📧 Gửi email chúc mừng & PDF văn bằng (Celery)")
    def send_congratulation_email_action(self, request, queryset):
        from .tasks import send_degree_congratulation_email
        count = 0
        errors = 0
        for degree in queryset:
            try:
                send_degree_congratulation_email.delay(degree.id)
                count += 1
            except Exception as e:
                errors += 1
                self.message_user(request, f"Lỗi gửi email cho {degree.student.full_name}: {str(e)}", level=messages.ERROR)
        if count > 0:
            self.message_user(
                request,
                f"🚀 Đã gửi email chúc mừng kèm file PDF văn bằng và mã QR cho {count} sinh viên thành công!",
                level=messages.SUCCESS
            )

    # --- 9. ACTION XUẤT SỔ GỐC BỘ GD&ĐT (EXCEL & PDF) ---
    @admin.action(description="📋 Xuất Sổ gốc Bộ GD&ĐT (Excel) cho các bằng đã chọn")
    def export_selected_so_goc_excel(self, request, queryset):
        from apps.reporting.so_goc_service import generate_so_goc_excel
        excel_bytes = generate_so_goc_excel(degrees=queryset)
        response = HttpResponse(
            excel_bytes,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="SoGoc_BoGDDT_Selected.xlsx"'
        return response

    @admin.action(description="📕 Xuất Sổ gốc Bộ GD&ĐT (PDF) cho các bằng đã chọn")
    def export_selected_so_goc_pdf(self, request, queryset):
        from apps.reporting.so_goc_service import generate_so_goc_pdf
        pdf_bytes = generate_so_goc_pdf(degrees=queryset)
        if not pdf_bytes:
            self.message_user(request, "Lỗi kết xuất PDF Sổ gốc.", level=messages.ERROR)
            return
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="SoGoc_BoGDDT_Selected.pdf"'
        return response

    # --- CẤU HÌNH ROUTE & VIEW FORM CẤP BẰNG ĐƠN LẺ ---
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('create-single/', self.admin_site.admin_view(self.create_single_degree_view), name='degrees_create_single'),
        ]
        return custom_urls + urls

    def add_view(self, request, form_url='', extra_context=None):
        """Bấm '+ Thêm Văn bằng số' sẽ tự động chuyển hướng đến Form cấp bằng đơn lẻ"""
        return redirect('admin:degrees_create_single')

    def create_single_degree_view(self, request):
        """View xử lý Form cấp phát văn bằng đơn lẻ cho Cán bộ nhập trực tiếp"""
        from .forms import SingleDegreeForm
        from django.utils import timezone

        if request.method == 'POST':
            form = SingleDegreeForm(request.POST)
            if form.is_valid():
                try:
                    degree = form.save(request.user)
                    self.message_user(
                        request,
                        f"🎉 Đã khởi tạo thành công văn bằng cho sinh viên {degree.student.full_name} ({degree.student.student_code})! Số hiệu: {degree.serial_number}. Trạng thái: {degree.get_status_display()}.",
                        level=messages.SUCCESS
                    )
                    return redirect('admin:degrees_degree_changelist')
                except Exception as e:
                    messages.error(request, f"Lỗi tạo văn bằng: {str(e)}")
        else:
            form = SingleDegreeForm()

        last_degree = Degree.objects.order_by('-id').first()
        next_id = (last_degree.id + 1) if last_degree else 1
        current_year = timezone.now().year
        preview_serial = f"CTUT-{current_year}-{next_id:06d}"
        preview_so_vao_so = f"{next_id:03d}/{current_year}/SGCB-CTUT"

        context = dict(
            self.admin_site.each_context(request),
            title="➕ Cấp phát Văn bằng Đơn lẻ",
            form=form,
            preview_serial=preview_serial,
            preview_so_vao_so=preview_so_vao_so,
        )
        return render(request, "admin/degrees/create_single.html", context)

