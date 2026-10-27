from celery import shared_task
from django.utils import timezone
import logging
logger = logging.getLogger(__name__)
# Số block xác nhận tối thiểu trước khi coi giao dịch là CONFIRMED
REQUIRED_CONFIRMATIONS = 3
@shared_task(bind=True, max_retries=40, default_retry_delay=15)
def sync_transaction(self, tx_hash: str):
    """
    Task chung đồng bộ giao dịch Blockchain.
    Gọi từ:
      - blockchain/admin.py  : sau khi Issuer ký phát hành qua MetaMask
      - revocation/views.py  : sau khi Issuer ký thu hồi qua MetaMask (Nghĩa - N4)
    """
    from apps.blockchain.models import BlockchainTransaction
    from apps.blockchain.client import BlockchainClient
    try:
        tx_record = BlockchainTransaction.objects.get(tx_hash=tx_hash)
    except BlockchainTransaction.DoesNotExist:
        logger.warning(f"[sync_transaction] Không tìm thấy bản ghi cho tx_hash={tx_hash}")
        return
    if tx_record.status != 'pending':
        logger.info(f"[sync_transaction] tx_hash={tx_hash} đã xử lý (status={tx_record.status}), bỏ qua.")
        return
    
    try:
        client = BlockchainClient()
        w3 = client.w3
        if not w3.is_connected():
            logger.warning(f"[sync_transaction] Không kết nối được blockchain, sẽ retry.")
            raise self.retry()
        # ── 1. Lấy receipt ───────────────────────────────────────────────────
        receipt = w3.eth.get_transaction_receipt(tx_hash)
        if receipt is None:
            logger.info(f"[sync_transaction] tx={tx_hash} chưa được mine, retry...")
            raise self.retry()
        # ── 2. Kiểm tra số xác nhận ──────────────────────────────────────────
        current_block = w3.eth.block_number
        confirmations = current_block - receipt['blockNumber']
        if confirmations < REQUIRED_CONFIRMATIONS:
            logger.info(
                f"[sync_transaction] tx={tx_hash[:10]}... có {confirmations}/{REQUIRED_CONFIRMATIONS} xác nhận, retry..."
            )
            raise self.retry()
        # ── 3. Giao dịch bị revert (status = 0) ─────────────────────────────
        if receipt['status'] == 0:
            logger.error(f"[sync_transaction] tx={tx_hash} bị REVERT trên chain!")
            tx_record.status = 'failed'
            tx_record.save(update_fields=['status'])
            _handle_tx_failed(tx_record)
            return
        # ── 4. Giao dịch thành công ──────────────────────────────────────────
        tx_record.status = 'confirmed'
        tx_record.block_number = receipt['blockNumber']
        tx_record.gas_used = receipt['gasUsed']
        tx_record.save(update_fields=['status', 'block_number', 'gas_used'])
        logger.info(
            f"[sync_transaction] tx={tx_hash[:10]}... CONFIRMED "
            f"block={receipt['blockNumber']} gas={receipt['gasUsed']}"
        )
        # Phân nhánh xử lý theo loại giao dịch
        if tx_record.operation_type == 'ISSUE' and tx_record.issuance_batch:
            _handle_issue_confirmed(tx_record, receipt, client)
        elif tx_record.operation_type in ('REVOKE', 'RETRY'):
            _handle_revoke_confirmed(tx_record)
            
    except Exception as exc:
        # Nếu là retry exception thì re-raise, không log lỗi
        if isinstance(exc, self.MaxRetriesExceededError):
            logger.error(f"[sync_transaction] tx={tx_hash} hết số lần retry!")
            tx_record.status = 'failed'
            tx_record.save(update_fields=['status'])
            _handle_tx_failed(tx_record)
        else:
            logger.warning(f"[sync_transaction] Lỗi tạm thời: {exc}, sẽ retry...")
            raise self.retry(exc=exc)

# ─────────────────────────────────────────────────────────────
#  HANDLERS NỘI BỘ
# ─────────────────────────────────────────────────────────────
def _handle_issue_confirmed(tx_record, receipt, client):
    """
    Sau khi giao dịch ISSUE (storeMerkleRoot) được xác nhận:
      1. Đọc event MerkleRootStored để lấy batchId.
      2. Cập nhật IssuanceBatch -> CONFIRMED.
      3. Chuyển Degree -> ISSUED.
    """
    from apps.blockchain.models import IssuanceBatch
    from apps.degrees.models import Degree
    issuance_batch = tx_record.issuance_batch
    chain_batch_id = None
    
    # ĐÃ SỬA: Đổi BatchStored() -> MerkleRootStored()
    try:
        logs = client.contract.events.MerkleRootStored().process_receipt(receipt)
        if logs:
            raw_id = logs[0]['args']['batchId']
            chain_batch_id = raw_id.hex() if hasattr(raw_id, 'hex') else str(raw_id)
            logger.info(f"[sync_transaction] Đọc được batchId={chain_batch_id} từ event MerkleRootStored.")
    except Exception as e:
        logger.warning(f"[sync_transaction] Không đọc được event MerkleRootStored: {e}")
        # Tự tính batchId từ tên đợt
        chain_batch_id = client.batch_id_of(issuance_batch.graduation_batch.name)
        
    # Cập nhật IssuanceBatch
    update_fields = ['status', 'confirmed_at']
    issuance_batch.status = 'CONFIRMED'
    issuance_batch.confirmed_at = timezone.now()
    if chain_batch_id:
        issuance_batch.chain_id = chain_batch_id if chain_batch_id.startswith('0x') else f"0x{chain_batch_id}"
        update_fields.append('chain_id')
    issuance_batch.save(update_fields=update_fields)

    # Chuyển tất cả Degree thuộc đợt này sang ISSUED
    count = Degree.objects.filter(
        batch=issuance_batch.graduation_batch,
        status='ISSUANCE_PENDING'
    ).update(status='ISSUED', generated_at=timezone.now())
    logger.info(
        f"[sync_transaction] IssuanceBatch #{issuance_batch.pk} CONFIRMED. "
        f"Đã chuyển {count} Degree sang ISSUED."
    )
def _handle_revoke_confirmed(tx_record):
    """
    Sau khi giao dịch REVOKE được xác nhận:
      Chuyển Degree liên quan sang REVOKED.
    """
    if tx_record.degree and tx_record.degree.status != 'REVOKED':
        tx_record.degree.status = 'REVOKED'
        tx_record.degree.save(update_fields=['status'])
        logger.info(
            f"[sync_transaction] Degree #{tx_record.degree.pk} đã chuyển sang REVOKED."
        )
        
def _handle_tx_failed(tx_record):
    """
    Xử lý khi giao dịch thất bại:
      - ISSUE thất bại: Degree về APPROVED để có thể retry phát hành.
      - REVOKE thất bại: giữ nguyên trạng thái.
    """
    if tx_record.operation_type == 'ISSUE' and tx_record.issuance_batch:
        from apps.degrees.models import Degree
        count = Degree.objects.filter(
            batch=tx_record.issuance_batch.graduation_batch,
            status='ISSUANCE_PENDING'
        ).update(status='APPROVED')
        logger.warning(
            f"[sync_transaction] Giao dịch ISSUE thất bại. "
            f"Đã trả {count} Degree về APPROVED để retry."
        )