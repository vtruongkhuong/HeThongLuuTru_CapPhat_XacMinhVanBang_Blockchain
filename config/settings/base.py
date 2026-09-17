"""
Cấu hình chung cho toàn bộ project (dev + prod kế thừa từ đây).
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'change-me')

INSTALLED_APPS = [
    # Unfold PHẢI đứng trước django.contrib.admin để override giao diện admin
    'unfold',
    'unfold.contrib.filters',
    'unfold.contrib.forms',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Local apps
    'apps.core',
    'apps.accounts',
    'apps.academic',
    'apps.students',
    'apps.graduation',
    'apps.degrees',
    'apps.workflow',
    'apps.blockchain',
    'apps.revocation',
    'apps.verification',
    'apps.student_portal',
    'apps.audit',
    'apps.reporting',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.audit.middleware.AuditLogMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

AUTH_USER_MODEL = 'accounts.User'

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'accounts:login'

LANGUAGE_CODE = 'vi'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Celery
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')

# Blockchain
WEB3_PROVIDER_URL = os.getenv('WEB3_PROVIDER_URL', 'http://127.0.0.1:8545')
CHAIN_ID = int(os.getenv('CHAIN_ID', '1337'))
ISSUER_PRIVATE_KEY = os.getenv('ISSUER_PRIVATE_KEY', '')
CONTRACT_ADDRESS = os.getenv('CONTRACT_ADDRESS', '')


# ==============================================================================
# Unfold — theme cho Django Admin (https://unfoldadmin.com)
# ==============================================================================
from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

UNFOLD = {
    "SITE_TITLE": "Văn bằng Blockchain - Admin",
    "SITE_HEADER": "Hệ thống Quản lý Văn bằng Blockchain",
    "SITE_SYMBOL": "school",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "LOGIN": {
        "image": None,
    },
    "COLORS": {
        "primary": {
            "50": "238 242 255", "100": "224 231 255", "200": "199 210 254",
            "300": "165 180 252", "400": "129 140 248", "500": "99 102 241",
            "600": "79 70 229", "700": "67 56 202", "800": "55 48 163",
            "900": "49 46 129", "950": "30 27 75",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": _("Tài khoản & Phân quyền"),
                "separator": True,
                "items": [
                    {
                        "title": _("Người dùng"),
                        "icon": "person",
                        "link": reverse_lazy("admin:accounts_user_changelist"),
                    },
                    {
                        "title": _("Vai trò"),
                        "icon": "shield",
                        "link": reverse_lazy("admin:accounts_role_changelist"),
                    },
                    {
                        "title": _("Quyền hạn"),
                        "icon": "key",
                        "link": reverse_lazy("admin:accounts_permission_changelist"),
                    },
                ],
            },
            {
                "title": _("Danh mục đào tạo"),
                "separator": True,
                "items": [
                    {
                        "title": _("Khoa"),
                        "icon": "corporate_fare",
                        "link": reverse_lazy("admin:academic_faculty_changelist"),
                    },
                    {
                        "title": _("Ngành"),
                        "icon": "school",
                        "link": reverse_lazy("admin:academic_major_changelist"),
                    },
                    {
                        "title": "Đợt tốt nghiệp",
                        "icon": "calendar_month", # Icon cuốn lịch cho đúng chất sự kiện
                        "link": reverse_lazy("admin:graduation_graduationbatch_changelist"),
                    },
                    {
                        "title": _("Loại văn bằng"),
                        "icon": "workspace_premium",
                        "link": reverse_lazy("admin:academic_degreetype_changelist"),
                    },
                ],
            },
            {
                "title": _("Sinh viên"),
                "separator": True,
                "items": [
                    {
                        "title": _("Danh sách sinh viên"),
                        "icon": "groups",
                        "link": reverse_lazy("admin:students_student_changelist"),
                    },
                    {
                        "title": _("Lịch sử import"),
                        "icon": "upload_file",
                        "link": reverse_lazy("admin:students_importbatch_changelist"),
                    },
                ],
            },
        ],
    },
}
