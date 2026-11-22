import os
from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import redirect, render
from apps.degrees.models import Degree


def ipfs_viewer_view(request, cid):
    """
    Trạm điều phối xem file IPFS:
    Nếu có file PDF cục bộ thì phục vụ trực tiếp để xem ngay lập tức mà không bị timeout,
    nếu không có thì chuyển hướng sang IPFS Gateway công cộng.
    """
    degree = Degree.objects.filter(ipfs_cid=cid).first()
    if degree and degree.pdf_path:
        media_root = getattr(settings, 'MEDIA_ROOT', os.path.join(settings.BASE_DIR, 'media'))
        full_path = os.path.join(media_root, degree.pdf_path)
        if os.path.exists(full_path):
            with open(full_path, 'rb') as f:
                pdf_data = f.read()
            response = HttpResponse(pdf_data, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="IPFS_{cid[:10]}_{degree.student.student_code}.pdf"'
            return response

    # Fallback chuyển hướng Gateway
    return redirect(f"https://ipfs.io/ipfs/{cid}")


def transaction_list_view(request):
    """
    [Nghĩa - Task 18] Blockchain TX Explorer Mini:
    Trang quản trị tra cứu trực tiếp toàn bộ các giao dịch On-chain phát hành và thu hồi
    văn bằng trên mạng Ethereum Sepolia (TxHash, Gas used, Block number, Trạng thái).
    Tích hợp 100% chuẩn giao diện Unfold Admin đồng bộ toàn hệ thống.
    """
    from django.contrib.admin import site as admin_site
    from apps.blockchain.models import BlockchainTransaction
    from apps.graduation.models import GraduationBatch
    from django.db.models import Q

    # Kiểm tra quyền nhân viên / admin
    if not request.user.is_authenticated or not request.user.is_staff:
        from django.contrib.auth.views import redirect_to_login
        return redirect_to_login(request.get_full_path(), login_url='accounts:login')

    # Xử lý nút "Đồng bộ On-Chain" thủ công từ giao diện
    if request.GET.get('sync') == '1':
        from django.contrib import messages
        from apps.blockchain.client import BlockchainClient
        synced_count = 0
        try:
            client = BlockchainClient()
            w3 = client.w3
            if w3.is_connected():
                pending_txs = BlockchainTransaction.objects.filter(
                    Q(block_number__isnull=True) | Q(gas_used__isnull=True) | Q(status__iexact='pending')
                )
                for tx in pending_txs:
                    try:
                        receipt = w3.eth.get_transaction_receipt(tx.tx_hash)
                        if receipt:
                            tx.block_number = receipt.blockNumber
                            tx.gas_used = receipt.gasUsed
                            tx.status = 'confirmed' if receipt.status == 1 else 'failed'
                            tx.save(update_fields=['block_number', 'gas_used', 'status'])
                            synced_count += 1
                    except Exception:
                        pass
                if synced_count > 0:
                    messages.success(request, f"Đã đồng bộ thành công {synced_count} giao dịch mới nhất từ Ethereum Sepolia Testnet!")
                else:
                    messages.info(request, "Tất cả giao dịch trên hệ thống đã khớp nối chính xác với Sepolia Testnet.")
            else:
                messages.warning(request, "Không thể kết nối đến Sepolia RPC node để đồng bộ.")
        except Exception as e:
            messages.error(request, f"Lỗi khi đồng bộ dữ liệu On-Chain: {e}")
        return redirect('admin_blockchain_transactions')

    batch_id = request.GET.get('batch_id', '').strip()
    op_type = request.GET.get('op_type', '').strip()
    status_filter = request.GET.get('status', '').strip()
    search_q = request.GET.get('q', '').strip()

    qs = BlockchainTransaction.objects.select_related(
        'issuance_batch', 'issuance_batch__graduation_batch', 'degree', 'degree__student', 'degree__batch'
    ).order_by('-created_at')

    # Bộ lọc theo đợt tốt nghiệp (liên kết qua issuance_batch hoặc degree)
    if batch_id:
        qs = qs.filter(
            Q(issuance_batch__graduation_batch_id=batch_id) |
            Q(degree__batch_id=batch_id)
        )

    # Bộ lọc theo loại thao tác
    if op_type:
        qs = qs.filter(operation_type__iexact=op_type)

    # Bộ lọc theo trạng thái
    if status_filter:
        qs = qs.filter(status__iexact=status_filter)

    # Tìm kiếm theo TxHash, MSSV, Họ tên sinh viên, Số hiệu văn bằng hoặc Tên đợt
    if search_q:
        qs = qs.filter(
            Q(tx_hash__icontains=search_q) |
            Q(degree__student__student_code__icontains=search_q) |
            Q(degree__student__full_name__icontains=search_q) |
            Q(degree__degree_number__icontains=search_q) |
            Q(issuance_batch__graduation_batch__name__icontains=search_q) |
            Q(degree__batch__name__icontains=search_q)
        )

    batches = GraduationBatch.objects.all().order_by('-id')

    total_tx = BlockchainTransaction.objects.count()
    confirmed_tx = BlockchainTransaction.objects.filter(status__iexact='confirmed').count()
    issue_tx = BlockchainTransaction.objects.filter(operation_type__iexact='ISSUE').count()
    revoke_tx = BlockchainTransaction.objects.filter(operation_type__iexact='REVOKE').count()

    tx_list = list(qs[:100])

    # Gắn thêm dữ liệu chi tiết của yêu cầu thu hồi (RevocationRequest)
    from apps.revocation.models import RevocationRequest
    tx_hashes = [tx.tx_hash for tx in tx_list if tx.tx_hash]
    if tx_hashes:
        rev_requests = RevocationRequest.objects.filter(tx_hash__in=tx_hashes).select_related(
            'degree', 'degree__student', 'degree__batch', 'reason_code', 'supersedes'
        )
        rev_map = {r.tx_hash: r for r in rev_requests}
        for tx in tx_list:
            if tx.tx_hash in rev_map:
                rev = rev_map[tx.tx_hash]
                tx.revocation_request = rev
                if not tx.degree and rev.degree:
                    tx.degree = rev.degree

    context = dict(
        admin_site.each_context(request),
        title="Blockchain Transaction Explorer",
        subtitle="Giám sát & Đối soát giao dịch On-Chain Sepolia Testnet (Chain ID: 11155111)",
        transactions=tx_list,
        batches=batches,
        selected_batch=batch_id,
        selected_op=op_type,
        selected_status=status_filter,
        search_query=search_q,
        stats={
            'total': total_tx,
            'confirmed': confirmed_tx,
            'issue': issue_tx,
            'revoke': revoke_tx,
        }
    )
    return render(request, 'admin/blockchain/transaction_list.html', context)
