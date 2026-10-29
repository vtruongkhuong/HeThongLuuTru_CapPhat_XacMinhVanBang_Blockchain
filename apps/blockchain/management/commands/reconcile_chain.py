from django.core.management.base import BaseCommand
from django.conf import settings
import sys
from web3 import Web3

from apps.blockchain.models import BlockchainTransaction, IssuanceBatch
from apps.degrees.models import Degree
from apps.blockchain.client import BlockchainClient


def reconcile_pending_transactions(w3=None):
    """Đối soát các giao dịch đang ở trạng thái pending trên chuỗi"""
    if w3 is None:
        try:
            client = BlockchainClient()
            w3 = client.w3
        except Exception:
            rpc_url = getattr(settings, 'WEB3_PROVIDER_URL', 'https://rpc.sepolia.org')
            w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 5}))

    pending_txs = BlockchainTransaction.objects.filter(status='pending')
    confirmed_count = 0
    failed_count = 0

    for tx in pending_txs:
        if not tx.tx_hash:
            continue
        try:
            receipt = w3.eth.get_transaction_receipt(tx.tx_hash)
            if receipt:
                if receipt.get('status') == 1:
                    tx.status = 'confirmed'
                    confirmed_count += 1
                else:
                    tx.status = 'failed'
                    failed_count += 1
                tx.save(update_fields=['status'])
        except Exception:
            continue

    return {'confirmed': confirmed_count, 'failed': failed_count}


def reconcile_merkle_roots(client=None):
    """
    Đối soát toàn vẹn mã Merkle Root giữa Database và Smart Contract.
    Phát hiện ngay lập tức nếu ai đó vào Database sửa lén dữ liệu băm.
    """
    if client is None:
        try:
            client = BlockchainClient()
        except Exception as e:
            return {'status': 'error', 'message': f"Không thể khởi tạo BlockchainClient: {e}"}

    batches = IssuanceBatch.objects.filter(status='CONFIRMED').exclude(chain_id__isnull=True).exclude(chain_id='')
    results = {
        'total_checked': 0,
        'valid_batches': 0,
        'tampered_batches': 0,
        'missing_on_chain': 0,
        'details': []
    }

    for ib in batches:
        results['total_checked'] += 1
        batch_name = ib.graduation_batch.name if ib.graduation_batch else f"Batch #{ib.id}"
        chain_batch_id = ib.chain_id

        chain_info = client.get_batch(chain_batch_id)
        if not chain_info or not chain_info.get('root') or chain_info['root'].replace('0x', '') == '0' * 64:
            results['missing_on_chain'] += 1
            results['details'].append({
                'batch_id': ib.id,
                'batch_name': batch_name,
                'status': 'MISSING_ON_CHAIN',
                'message': f"Đợt '{batch_name}' (ID: {chain_batch_id[:10]}...) chưa được xác nhận trên Blockchain Sepolia."
            })
            continue

        db_root = (ib.merkle_root or '').lower().replace('0x', '').strip()
        chain_root = chain_info['root'].lower().replace('0x', '').strip()

        if db_root != chain_root:
            results['tampered_batches'] += 1
            results['details'].append({
                'batch_id': ib.id,
                'batch_name': batch_name,
                'status': 'TAMPERED',
                'db_root': db_root,
                'chain_root': chain_root,
                'message': f"🚨 BÁO ĐỘNG GIAN LẬN: Merkle Root đợt '{batch_name}' bị sai lệch! DB={db_root[:10]}... != Chain={chain_root[:10]}..."
            })
        else:
            results['valid_batches'] += 1
            results['details'].append({
                'batch_id': ib.id,
                'batch_name': batch_name,
                'status': 'OK',
                'message': f"✅ Đợt '{batch_name}': Merkle Root khớp 100% với Smart Contract ({chain_root[:10]}...)"
            })

    return results


def reconcile_revocations(client=None):
    """
    Đối soát trạng thái thu hồi của văn bằng trên Smart Contract.
    """
    if client is None:
        try:
            client = BlockchainClient()
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _check_revoked_on_chain(clean_leaf_str):
        try:
            return client.contract.get_function_by_signature('verifyDegreeRevoked(string)')(clean_leaf_str).call()
        except Exception:
            try:
                return client.contract.get_function_by_signature('verifyDegreeRevoked(bytes32)')(bytes.fromhex(clean_leaf_str)).call()
            except Exception:
                return None

    # 1. Kiểm tra văn bằng REVOKED trong DB
    revoked_degrees = Degree.objects.filter(status='REVOKED').exclude(canonical_hash__isnull=True).exclude(canonical_hash='')[:3]
    mismatches = []
    checked_count = 0

    for d in revoked_degrees:
        checked_count += 1
        clean_leaf = d.canonical_hash.replace('0x', '')
        is_revoked_on_chain = _check_revoked_on_chain(clean_leaf)
        if is_revoked_on_chain is False:
            mismatches.append({
                'degree_id': d.id,
                'public_id': str(d.credential_public_id),
                'status': 'DB_REVOKED_CHAIN_ACTIVE',
                'message': f"Bằng {d.credential_public_id} trạng thái DB là REVOKED nhưng trên Chain chưa thu hồi!"
            })

    # 2. Kiểm tra văn bằng ISSUED trong DB xem có bị revoke lén trên Chain không
    issued_degrees = Degree.objects.filter(status='ISSUED').exclude(canonical_hash__isnull=True).exclude(canonical_hash='').order_by('-id')[:3]
    for d in issued_degrees:
        checked_count += 1
        clean_leaf = d.canonical_hash.replace('0x', '')
        is_revoked_on_chain = _check_revoked_on_chain(clean_leaf)
        if is_revoked_on_chain is True:
            mismatches.append({
                'degree_id': d.id,
                'public_id': str(d.credential_public_id),
                'status': 'CHAIN_REVOKED_DB_ACTIVE',
                'message': f"🚨 BÁO ĐỘNG: Bằng {d.credential_public_id} đã bị thu hồi trên Chain nhưng DB vẫn là ISSUED!"
            })

    return {
        'checked_count': checked_count,
        'mismatches_count': len(mismatches),
        'mismatches': mismatches
    }


def run_full_reconciliation():
    """Hàm tổng hợp đối soát toàn diện, phục vụ cả Celery Beat và CLI"""
    tx_results = reconcile_pending_transactions()
    root_results = reconcile_merkle_roots()
    rev_results = reconcile_revocations()
    return {
        'transactions': tx_results,
        'merkle_roots': root_results,
        'revocations': rev_results
    }


class Command(BaseCommand):
    help = 'Lệnh đối soát tự động: Kiểm tra tính toàn vẹn Merkle Root & Trạng thái giữa DB và Blockchain'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("🔍 Bắt đầu phiên đối soát Blockchain..."))
        sys.stdout.flush()

        # 1. Đối soát Giao dịch
        self.stdout.write("⏳ Đang đối soát các giao dịch pending...")
        sys.stdout.flush()
        tx_res = reconcile_pending_transactions()
        self.stdout.write(
            f"1. Giao dịch pending: {tx_res['confirmed']} confirmed, {tx_res['failed']} failed."
        )
        sys.stdout.flush()

        # 2. Đối soát Merkle Root
        self.stdout.write("⏳ Đang gọi Smart Contract đối soát Merkle Root...")
        sys.stdout.flush()
        root_res = reconcile_merkle_roots()
        self.stdout.write(f"2. Đối soát Merkle Root: Đã kiểm tra {root_res.get('total_checked', 0)} đợt.")
        for detail in root_res.get('details', []):
            if detail['status'] == 'OK':
                self.stdout.write(self.style.SUCCESS(f"   {detail['message']}"))
            elif detail['status'] == 'TAMPERED':
                self.stdout.write(self.style.ERROR(f"   {detail['message']}"))
            else:
                self.stdout.write(self.style.WARNING(f"   {detail['message']}"))
        sys.stdout.flush()

        if root_res.get('tampered_batches', 0) > 0:
            self.stdout.write(self.style.ERROR(
                f"\n🚨 CẢNH BÁO BẢO MẬT: Phát hiện {root_res['tampered_batches']} đợt có Merkle Root bị chỉnh sửa trái phép!"
            ))

        # 3. Đối soát Trạng thái thu hồi
        self.stdout.write("⏳ Đang đối soát trạng thái thu hồi...")
        sys.stdout.flush()
        rev_res = reconcile_revocations()
        self.stdout.write(f"3. Đối soát trạng thái thu hồi: {rev_res.get('mismatches_count', 0)} sai lệch.")
        for m in rev_res.get('mismatches', []):
            if 'BÁO ĐỘNG' in m['message']:
                self.stdout.write(self.style.ERROR(f"   {m['message']}"))
            else:
                self.stdout.write(self.style.WARNING(f"   {m['message']}"))

        self.stdout.write(self.style.SUCCESS("✨ Phiên đối soát hoàn tất."))
