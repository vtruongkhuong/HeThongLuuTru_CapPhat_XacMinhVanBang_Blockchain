from .base import *  # noqa
import os
import sys
import dj_database_url

DEBUG = True
ALLOWED_HOSTS = ['*']

# Tự động đọc biến DATABASE_URL từ file .env
DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Khi chạy lệnh 'python manage.py test', tự động chuyển sang SQLite trên RAM
# giúp chạy test tức thì và không bị kẹt kết nối (ObjectInUse) trên Neon Cloud
if 'test' in sys.argv:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }

INTERNAL_IPS = ['127.0.0.1']