from .models import AuditLog

def log_action(actor, action, entity_type, entity_id, old=None, new=None, request=None):
    
    ip_address = None
    request_id = None
    user_agent = None
    
    if request:
        # Lấy IP, Request ID và User Agent từ Middleware, kèm fallback
        ip_address = getattr(request, 'client_ip', request.META.get('REMOTE_ADDR'))
        request_id = getattr(request, 'request_id', None)
        user_agent = getattr(request, 'user_agent', request.META.get('HTTP_USER_AGENT'))

    return AuditLog.objects.create(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        old_value=old,
        new_value=new,
        ip_address=ip_address,
        request_id=request_id,
        user_agent=user_agent
    )