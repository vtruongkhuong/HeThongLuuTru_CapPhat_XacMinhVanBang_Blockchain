from .base import *  # noqa
import os
import sys
import dj_database_url
from dotenv import load_dotenv

# Ép nạp chính xác file .env từ thư mục gốc dự án
load_dotenv(BASE_DIR / '.env', override=True)

DEBUG = True
ALLOWED_HOSTS = ['*']

# Tự động đọc biến DATABASE_URL từ file .env (có sẵn fallback an toàn)
DEFAULT_DB_URL = (
    "postgresql://neondb_owner:npg_jT67dSXxZIih@"
    "ep-lingering-frost-b30wp3po-pooler.c-4.ap-southeast-1.aws.neon.tech/"
    "neondb?sslmode=require&channel_binding=require"
)

DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL', DEFAULT_DB_URL),
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
# Chế độ chạy Celery Eager (Local): Tự động thực thi ngay lập tức mà không cần bật Redis server
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
