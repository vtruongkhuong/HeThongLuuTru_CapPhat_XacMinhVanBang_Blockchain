from web3 import Web3
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
from django.conf import settings

from apps.blockchain.client import BlockchainClient
from .models import RevocationRequest
from . import services
from .admin import _user_has_role


def _build_unsigned_revoke_data(degree_identifier, reason_text=""):
    """
    Tạo dữ liệu giao dịch chưa ký (calldata hex) cho hàm revokeDegree trên Smart Contract.
    Hỗ trợ tự động cả khi ABI đã cập nhật hoặc chưa cập nhật.
    """
    try:
        client = BlockchainClient()
        if hasattr(client.contract.functions, 'revokeDegree'):
            fn = client.contract.functions.revokeDegree
            # Thử tạo calldata với 1 tham số (degree_id) hoặc 2 tham số (degree_id, reason)
            for args in ([str(degree_identifier)], [str(degree_identifier), str(reason_text)]):
                try:
                    tx = fn(*args).build_transaction({
                        'from': '0x0000000000000000000000000000000000000000',
                        'gas': 200000,
                        'gasPrice': 1000000000,
                        'nonce': 0,
                        'chainId': int(getattr(settings, 'CHAIN_ID', 11155111)),
                    })
                    if tx.get('data'):
                        return tx['data']
                except Exception:
                    continue
    except Exception:
        pass

    # Fallback: Tự mã hóa selector chuẩn EVM cho revokeDegree(string) nếu ABI cũ chưa có hàm này
    selector = Web3.keccak(text="revokeDegree(string)")[:4].hex()
    if not selector.startswith("0x"):
        selector = "0x" + selector
    encoded_str = str(degree_identifier).encode('utf-8').hex()
    offset = (32).to_bytes(32, 'big').hex()
    length = len(str(degree_identifier).encode('utf-8')).to_bytes(32, 'big').hex()
    padded_data = encoded_str.ljust(64, '0')
    return f"{selector}{offset}{length}{padded_data}"


@staff_member_required
def execute_revocation_metamask_view(request, pk):
    """
    Trang dành cho Issuer kết nối ví MetaMask ký lệnh thu hồi văn bằng trên Sepolia
    hoặc dùng nút Giao dịch giả để test luồng.
    """
    if not _user_has_role(request.user, ['issuer', 'super_admin']):
        messages.error(request, "Từ chối truy cập: Chỉ tài khoản có quyền Thực thi (Issuer) mới được ký thu hồi trên Blockchain!")
        return redirect('admin:revocation_revocationrequest_changelist')

    rev_request = get_object_or_404(RevocationRequest.objects.select_related('degree', 'reason_code'), pk=pk)
    degree = rev_request.degree

    degree_identifier = (
        getattr(degree, 'credential_public_id', None)
        or getattr(degree, 'degree_hash', None)
        or getattr(degree, 'serial_number', None)
        or str(degree.pk)
    )

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
                f"Đã thực thi thu hồi văn bằng thành công! Trạng thái văn bằng đã chuyển sang REVOKED (TxHash: {rev_request.tx_hash})."
            )
            return redirect('admin:revocation_revocationrequest_changelist')
        except ValidationError as e:
            error_msg = e.messages[0] if hasattr(e, 'messages') else str(e)
            messages.error(request, error_msg)
        except Exception as e:
            messages.error(request, f"Lỗi khi thực thi thu hồi: {e}")

    tx_data = _build_unsigned_revoke_data(degree_identifier, rev_request.reason_code.description)

    context = {
        'rev_request': rev_request,
        'degree': degree,
        'degree_identifier': degree_identifier,
        'contract_address': getattr(settings, 'CONTRACT_ADDRESS', ''),
        'chain_id': int(getattr(settings, 'CHAIN_ID', 11155111)),
        'tx_data': tx_data,
    }
    return render(request, 'revocation/execute_metamask.html', context)