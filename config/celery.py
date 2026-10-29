import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

app = Celery('vanbang_blockchain')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Cấu hình Celery Beat chạy định kỳ lệnh đối soát
app.conf.beat_schedule = {
    'reconcile-chain-every-midnight': {
        # Tạo một task bọc lệnh call_command để gọi 'reconcile_chain'
        'task': 'apps.blockchain.tasks.run_reconcile_chain', 
        # Chạy vào lúc 0h00 mỗi ngày
        'schedule': crontab(minute=0, hour=0), 
    },
}