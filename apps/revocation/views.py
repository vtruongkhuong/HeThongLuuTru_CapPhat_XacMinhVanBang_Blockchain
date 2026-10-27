from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
from django.conf import settings

from apps.blockchain.client import BlockchainClient
from .models import RevocationRequest
from . import services
from .admin import _user_has_role


@staff_member_required
def execute_revocation_metamask_view(request, pk):
    """
    [N7] Giao diện cho Issuer kết nối ví MetaMask ký lệnh revokeDegree(bytes32 batchId, bytes32 leaf, uint8 reason)
    trên mạng Sepolia theo Smart Contract v2.
    """
    if not _user_has_role(request.user, ['issuer', 'super_admin']):
        messages.error(request, "Từ chối truy cập: Chỉ tài khoản có quyền Thực thi (Issuer) mới được ký thu hồi trên Blockchain!")
        return redirect('admin:revocation_revocationrequest_changelist')

    rev_request = get_object_or_404(
        RevocationRequest.objects.select_related('degree', 'reason_code', 'degree__batch'),
        pk=pk
    )
    degree = rev_request.degree

    client = BlockchainClient()
    batch_name = degree.batch.name if degree.batch else "DefaultBatch"
    batch_id_hex = client.batch_id_of(batch_name)
    leaf_hex = getattr(degree, 'canonical_hash', None) or str(degree.credential_public_id)

    # Chuyển mã lý do sang dạng uint8
    reason_code_val = 1
    if rev_request.reason_code:
        if str(rev_request.reason_code.code).isdigit():
            reason_code_val = int(rev_request.reason_code.code)
        else:
            reason_map = {'SAI_THONG_TIN': 1, 'GIA_MAO': 2, 'KY_LUAT': 3, 'HUY_QUYET_DINH': 4}
            reason_code_val = reason_map.get(str(rev_request.reason_code.code).upper(), 1)

    # Sinh mã calldata chính xác cho hàm revokeDegree(bytes32,bytes32,uint8)
    tx_data = "0x"
    try:
        tx_data = client.build_revoke_tx_data(batch_id_hex, leaf_hex, reason_code_val)
    except Exception as e:
        messages.warning(request, f"Lưu ý tạo calldata thu hồi: {e}")

    if request.method == 'POST':
        tx_hash = request.POST.get('tx_hash', '').strip()
        try:
            services.execute(
                revocation_request=rev_request,
                executed_by=request.user,
                tx_hash=tx_hash or None,
                http_request=request
            )
            messages.success(
                request,
                f"Đã thực thi thu hồi văn bằng thành công! Giao dịch đang được đồng bộ trên Blockchain Sepolia (TxHash: {tx_hash})."
            )
            return redirect('admin:revocation_revocationrequest_changelist')
        except ValidationError as e:
            error_msg = e.messages[0] if hasattr(e, 'messages') else str(e)
            messages.error(request, error_msg)
        except Exception as e:
            messages.error(request, f"Lỗi khi thực thi thu hồi: {e}")

    degree_identifier = (
        getattr(degree, 'credential_public_id', None)
        or getattr(degree, 'canonical_hash', None)
        or getattr(degree, 'serial_number', None)
        or str(degree.pk)
    )

    context = {
        'rev_request': rev_request,
        'degree': degree,
        'degree_identifier': degree_identifier,
        'contract_address': getattr(settings, 'CONTRACT_ADDRESS', '0xEDA267AE063b32A8b23B97e67a5dD355891cbd1D'),
        'chain_id': int(getattr(settings, 'CHAIN_ID', 11155111)),
        'tx_data': tx_data,
        'batch_id_hex': batch_id_hex,
        'leaf_hex': leaf_hex,
        'reason_code_val': reason_code_val,
    }
    return render(request, 'revocation/execute_metamask.html', context)
