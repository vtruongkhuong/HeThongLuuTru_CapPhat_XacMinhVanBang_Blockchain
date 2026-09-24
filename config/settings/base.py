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

    #Google
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',

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

SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.audit.middleware.AuditLogMiddleware',
    "allauth.account.middleware.AccountMiddleware",
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

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

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

# --- HÀM HELPER: KIỂM TRA QUYỀN ĐỂ ẨN/HIỆN MENU ĐỘNG ---
def check_menu_role(request, allowed_roles):
    """Ẩn menu nếu user không có role nằm trong danh sách allowed_roles."""
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return False
    if request.user.is_superuser:
        return True
    try:
        user_roles = request.user.roles.values_list('code', flat=True)
        return any(role in user_roles for role in allowed_roles)
    except Exception:
        return False

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
                        "permission": lambda request: request.user.is_superuser, # Chỉ Admin tối cao
                    },
                    {
                        "title": _("Vai trò"),
                        "icon": "shield",
                        "link": reverse_lazy("admin:accounts_role_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("Quyền hạn"),
                        "icon": "key",
                        "link": reverse_lazy("admin:accounts_permission_changelist"),
                        "permission": lambda request: request.user.is_superuser,
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
                        "permission": lambda request: check_menu_role(request, ['officer_a', 'academic_staff']),
                    },
                    {
                        "title": _("Ngành"),
                        "icon": "school",
                        "link": reverse_lazy("admin:academic_major_changelist"),
                        "permission": lambda request: check_menu_role(request, ['officer_a', 'academic_staff']),
                    },
                    {
                        "title": "Đợt tốt nghiệp",
                        "icon": "calendar_month", 
                        "link": reverse_lazy("admin:graduation_graduationbatch_changelist"),
                        # Cả Nhập liệu và Phê duyệt đều cần thấy menu này
                        "permission": lambda request: check_menu_role(request, ['officer_a', 'academic_staff', 'officer_b', 'reviewer', 'approver']),
                    },
                    {
                        "title": _("Loại văn bằng"),
                        "icon": "workspace_premium",
                        "link": reverse_lazy("admin:academic_degreetype_changelist"),
                        "permission": lambda request: check_menu_role(request, ['officer_a', 'academic_staff']),
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
                        "permission": lambda request: check_menu_role(request, ['officer_a', 'academic_staff']),
                    },
                    {
                        "title": _("Lịch sử import"),
                        "icon": "upload_file",
                        "link": reverse_lazy("admin:students_importbatch_changelist"),
                        "permission": lambda request: check_menu_role(request, ['officer_a', 'academic_staff']),
                    },
                ],
            },
        ],
    },
}