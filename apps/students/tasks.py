"""
Celery task: import sinh viên bất đồng bộ, để không block request khi file lớn.

Idempotency: nếu task bị retry (do worker crash giữa chừng), các Student đã
tạo thành công sẽ không bị tạo lại nhờ check dedup trong importers.run_import().
Task chỉ cập nhật lại batch.status/kết quả, không tạo batch mới.
"""
from celery import shared_task
from celery.utils.log import get_task_logger

from .models import ImportBatch, ImportBatchItem
from .importers import run_import

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_student_import(self, batch_id: int):
    """
    Args:
        batch_id: PK của ImportBatch cần xử lý.
    """
    try:
        batch = ImportBatch.objects.get(pk=batch_id)
    except ImportBatch.DoesNotExist:
        logger.error("ImportBatch %s không tồn tại, bỏ qua task.", batch_id)
        return

    if batch.status == 'completed':
        logger.info("Batch %s đã completed trước đó, bỏ qua (idempotent).", batch_id)
        return

    batch.status = 'processing'
    batch.save(update_fields=['status'])

    try:
        result = run_import(batch)
        batch.total_rows = result.total_rows
        batch.success_rows = result.success_rows
        batch.error_rows = result.error_rows
        batch.error_detail = result.errors
        batch.status = 'completed' if result.error_rows == 0 else 'completed'
        # Lưu ý: vẫn đánh dấu 'completed' kể cả có lỗi từng dòng, vì lỗi
        # từng dòng không phải lỗi hệ thống — cán bộ xem error_detail để sửa
        # rồi import lại riêng các dòng lỗi.
        batch.save(update_fields=['total_rows', 'success_rows', 'error_rows', 'error_detail', 'status'])
        logger.info(
            "Batch %s hoàn tất: %s/%s dòng thành công",
            batch_id, result.success_rows, result.total_rows
        )
    except Exception as exc:
        logger.exception("Batch %s thất bại: %s", batch_id, exc)
        batch.status = 'failed'
        batch.error_detail = [{'row': 0, 'error': str(exc)}]
        batch.save(update_fields=['status', 'error_detail'])
        raise self.retry(exc=exc)
