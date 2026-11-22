import logging
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import APIClient

logger = logging.getLogger(__name__)


class APIKeyAuthentication(BaseAuthentication):
    """
    Xác thực bằng header X-API-Key.
    - Không có key    → None (tiếp tục, permission_classes sẽ chặn nếu cần)
    - Key sai/inactive → 401 AuthenticationFailed
    - Vượt quota       → 403 AuthenticationFailed
    """

    def authenticate(self, request):
        key = request.headers.get('X-API-Key')
        if not key:
            return None

        client = APIClient.objects.filter(api_key=key, is_active=True).first()
        if not client:
            raise AuthenticationFailed('API Key không hợp lệ hoặc đã bị thu hồi.')

        if client.usage_today >= client.quota_per_day:
            raise AuthenticationFailed(
                f'Vượt quota ngày ({client.quota_per_day} request/ngày).'
            )

        # Tăng counter (dùng F() để tránh race condition)
        APIClient.objects.filter(pk=client.pk).update(
            usage_today=client.usage_today + 1
        )

        # Ghi AuditLog
        try:
            from apps.audit.models import AuditLog
            from apps.verification.throttling import get_client_ip
            AuditLog.objects.create(
                actor=None,
                action='OTHER',
                entity_type='APIClient',
                entity_id=client.name,
                new_value={'endpoint': request.path, 'ip': get_client_ip(request)},
            )
        except Exception as e:
            logger.warning("Không ghi được AuditLog: %s", e)

        return (client, None)

    def authenticate_header(self, request):
        return 'X-API-Key'


from drf_spectacular.extensions import OpenApiAuthenticationExtension


class APIKeyScheme(OpenApiAuthenticationExtension):
    """Đăng ký bảo mật X-API-Key vào tài liệu Swagger / OpenAPI."""
    target_class = 'apps.api.authentication.APIKeyAuthentication'
    name = 'ApiKeyAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'apiKey',
            'in': 'header',
            'name': 'X-API-Key',
            'description': 'Nhập mã API Key của doanh nghiệp được cấp trong Django Admin.',
        }
