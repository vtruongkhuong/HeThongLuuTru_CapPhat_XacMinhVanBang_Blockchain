from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from .services import log_action

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    log_action(actor=user, action='LOGIN', entity_type='User', entity_id=user.id, request=request)

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    if user:
        log_action(actor=user, action='LOGOUT', entity_type='User', entity_id=user.id, request=request)