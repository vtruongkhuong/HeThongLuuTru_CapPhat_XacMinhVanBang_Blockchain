from django.apps import AppConfig

class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.audit'
    verbose_name = 'Giám sát hệ thống'

    def ready(self):
        # Nơi này sẽ báo cho Django biết là "Hãy kích hoạt tính năng lắng nghe tín hiệu (signals) khi khởi động"
        import apps.audit.signals