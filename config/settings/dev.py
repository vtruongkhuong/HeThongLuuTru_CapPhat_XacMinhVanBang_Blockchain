from .base import *  # noqa
import dj_database_url
DEBUG = True
ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': dj_database_url.config(
        # Dán cái chuỗi Connection String bạn vừa copy bên Neon vào đây:
        default='postgresql://neondb_owner:npg_jT67dSXxZIih@ep-lingering-frost-b30wp3po-pooler.c-4.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require',
        conn_max_age=600,
        conn_health_checks=True,
    )
}

INTERNAL_IPS = ['127.0.0.1']
