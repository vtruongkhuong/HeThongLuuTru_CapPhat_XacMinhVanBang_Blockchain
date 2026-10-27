import secrets
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError

from apps.workflow.services import ensure_different_actors, transition
from .models import RevocationRequest


def _safe_audit_log(actor, action, entity_type, entity_id, old=None, new=None, http_request=None):
    """Tự động gọi hàm ghi log của Khiêm (H1) nếu đã có, không gây lỗi nếu chưa có"""
    try:
        from apps.audit.services import log_action
        log_action(
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            old=old,
            new=new,
            request=http_request
        )
    except Exception:
        pass


def validate_degree_can_be_revoked(degree, exclude_request_id=None):
    """Kiểm tra điều kiện: Văn bằng phải đang ISSUED và chưa từng bị thu hồi / đang chờ thu hồi"""
    if degree.status == 'REVOKED':
        raise ValidationError("Văn bằng này đã bị thu hồi trước đó (không thể thu hồi hai lần).")

    if degree.status != 'ISSUED':
        raise ValidationError(
            f"Chỉ có thể thu hồi văn bằng đang ở trạng thái 'ISSUED' (Trạng thái hiện tại: {degree.status})."
        )

    existing_qs = RevocationRequest.objects.filter(
        degree=degree,
        status__in=['PENDING', 'APPROVED', 'EXECUTED']
    )
    if exclude_request_id:
        existing_qs = existing_qs.exclude(pk=exclude_request_id)

    if existing_qs.exists():
        raise ValidationError("Văn bằng này đã có yêu cầu thu hồi đang xử lý hoặc đã thực thi (không thể thu hồi hai lần).")


@transaction.atomic
def request(degree, reason_code, requested_by, description="", supersedes=None, http_request=None):
    """Bước 1 (Officer A): Tạo yêu cầu thu hồi văn bằng"""
    validate_degree_can_be_revoked(degree)

    if supersedes and supersedes.pk == degree.pk:
        raise ValidationError("Văn bằng thay thế (supersedes) không được trùng với văn bằng bị thu hồi.")

    rev_request = RevocationRequest.objects.create(
        degree=degree,
        reason_code=reason_code,
        description=description,
        requested_by=requested_by,
        supersedes=supersedes,
        status='PENDING'
    )

    _safe_audit_log(
        actor=requested_by,
        action='REVOCATION_REQUESTED',
        entity_type='RevocationRequest',
        entity_id=rev_request.pk,
        new={'status': 'PENDING', 'degree_id': degree.pk, 'reason': reason_code.code},
        http_request=http_request
    )
    return rev_request


@transaction.atomic
def approve(revocation_request, approved_by, http_request=None):
    """Bước 2 (Officer B): Duyệt yêu cầu thu hồi"""
    if revocation_request.status != 'PENDING':
        raise ValidationError("Chỉ có thể duyệt yêu cầu đang ở trạng thái Chờ duyệt (PENDING).")

    validate_degree_can_be_revoked(revocation_request.degree, exclude_request_id=revocation_request.pk)

    # Kiểm tra quy tắc 4-eyes: Người duyệt phải khác người tạo yêu cầu
    ensure_different_actors(revocation_request.requested_by, approved_by)

    old_status = revocation_request.status
    revocation_request.approved_by = approved_by
    revocation_request.approved_at = timezone.now()
    revocation_request.status = 'APPROVED'
    revocation_request.save()

    _safe_audit_log(
        actor=approved_by,
        action='REVOCATION_APPROVED',
        entity_type='RevocationRequest',
        entity_id=revocation_request.pk,
        old={'status': old_status},
        new={'status': 'APPROVED', 'approved_by': approved_by.pk},
        http_request=http_request
    )
    return revocation_request


@transaction.atomic
def reject(revocation_request, rejected_by, http_request=None):
    """Từ chối yêu cầu thu hồi"""
    if revocation_request.status != 'PENDING':
        raise ValidationError("Chỉ có thể từ chối yêu cầu đang ở trạng thái Chờ duyệt (PENDING).")

    ensure_different_actors(revocation_request.requested_by, rejected_by)

    old_status = revocation_request.status
    revocation_request.approved_by = rejected_by
    revocation_request.approved_at = timezone.now()
    revocation_request.status = 'REJECTED'
    revocation_request.save()

    _safe_audit_log(
        actor=rejected_by,
        action='REVOCATION_REJECTED',
        entity_type='RevocationRequest',
        entity_id=revocation_request.pk,
        old={'status': old_status},
        new={'status': 'REJECTED'},
        http_request=http_request
    )
    return revocation_request


@transaction.atomic
def execute(revocation_request, executed_by, tx_hash=None, supersedes=None, http_request=None):
    """
    [N7] Bước 3 (Issuer): Thực thi thu hồi trên Blockchain.
    Tạo BlockchainTransaction và gọi task sync_transaction của Khương để chờ xác nhận trên Sepolia.
    """
    if revocation_request.status == 'EXECUTED':
        raise ValidationError("Yêu cầu thu hồi này đã được thực thi trước đó.")

    if revocation_request.status != 'APPROVED':
        raise ValidationError("Yêu cầu thu hồi phải được Officer B phê duyệt (APPROVED) trước khi thực thi.")

    degree = revocation_request.degree
    if degree.status == 'REVOKED':
        raise ValidationError("Văn bằng này đã bị thu hồi trước đó (không thể thu hồi hai lần).")
    if degree.status != 'ISSUED':
        raise ValidationError("Chỉ có thể thu hồi văn bằng đang ở trạng thái ISSUED.")

    # Quy tắc 4-mắt / 3-bước: 3 người khác nhau
    ensure_different_actors(
        revocation_request.requested_by,
        revocation_request.approved_by,
        executed_by
    )

    if not tx_hash:
        tx_hash = "0x" + secrets.token_hex(32)

    if supersedes:
        revocation_request.supersedes = supersedes

    # 1. Cập nhật trạng thái RevocationRequest
    revocation_request.executed_by = executed_by
    revocation_request.executed_at = timezone.now()
    revocation_request.tx_hash = tx_hash
    revocation_request.status = 'EXECUTED'
    revocation_request.save()

    # 2. Tạo bản ghi BlockchainTransaction liên kết
    from apps.blockchain.models import BlockchainTransaction
    tx_record, _ = BlockchainTransaction.objects.get_or_create(
        tx_hash=tx_hash,
        defaults={
            'operation_type': 'REVOKE',
            'degree': degree,
            'submitted_by': executed_by,
            'status': 'pending',
        }
    )
    if tx_record.degree != degree or tx_record.operation_type != 'REVOKE':
        tx_record.degree = degree
        tx_record.operation_type = 'REVOKE'
        tx_record.save(update_fields=['degree', 'operation_type'])

    # 3. Chuyển trạng thái Degree sang REVOKED
    degree.status = 'REVOKED'
    degree.save(update_fields=['status'])

    # 4. Kích hoạt task đồng bộ giao dịch Celery (sync_transaction của Khương)
    try:
        from apps.blockchain.tasks import sync_transaction
        sync_transaction.delay(tx_hash)
    except Exception:
        pass

    _safe_audit_log(
        actor=executed_by,
        action='REVOCATION_EXECUTED',
        entity_type='RevocationRequest',
        entity_id=revocation_request.pk,
        new={'status': 'EXECUTED', 'tx_hash': tx_hash},
        http_request=http_request
    )
    return revocation_request
