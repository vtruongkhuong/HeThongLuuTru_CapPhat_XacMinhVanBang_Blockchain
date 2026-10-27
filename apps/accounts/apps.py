from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = 'Quản lý Tài khoản & Phân quyền'

    def ready(self):
        import apps.accounts.signals  # noqa
