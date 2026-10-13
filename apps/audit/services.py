from .models import AuditLog

def log_action(actor, action, entity_type, entity_id, old=None, new=None, request=None):
    """
    Hàm chuẩn để ghi log hệ thống. Khương và Nghĩa sẽ import hàm này.
    """
    ip_address = None
    request_id = None
    
    if request:
        # Lấy IP và Request ID đã được Middleware gắn vào
        ip_address = getattr(request, 'client_ip', None)
        request_id = getattr(request, 'request_id', None)

    return AuditLog.objects.create(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        old_value=old,
        new_value=new,
        ip_address=ip_address,
        request_id=request_id
    )