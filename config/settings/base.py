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
    'django.middleware.locale.LocaleMiddleware',
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
    'apps.accounts.backends.EmailOrUsernameModelBackend',
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

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Celery
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')

# Blockchain – Non-custodial: KHÔNG lưu private key của Issuer trên server
WEB3_PROVIDER_URL = os.getenv('WEB3_PROVIDER_URL', 'https://eth-sepolia.g.alchemy.com/v2/alch_ZWdSTTjsLh7SPMKrNskaj')
CHAIN_ID = int(os.getenv('CHAIN_ID', '11155111'))
CONTRACT_ADDRESS = os.getenv('CONTRACT_ADDRESS', '0xEDA267AE063b32A8b23B97e67a5dD355891cbd1D')

# Allauth & Google OAuth
ACCOUNT_LOGIN_METHODS = {'username', 'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_ADAPTER = 'apps.accounts.adapters.CustomSocialAccountAdapter'
ACCOUNT_ADAPTER = 'apps.accounts.adapters.CustomAccountAdapter'
SOCIALACCOUNT_AUTO_SIGNUP = True

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'OAUTH_PKCE_ENABLED': True,
    }
}
_google_id = os.getenv('GOOGLE_CLIENT_ID', '').strip()
_google_secret = os.getenv('GOOGLE_CLIENT_SECRET', '').strip()
if _google_id and _google_secret:
    SOCIALACCOUNT_PROVIDERS['google']['APP'] = {
        'client_id': _google_id,
        'secret': _google_secret,
        'key': ''
    }


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
        user_roles = request.user.roles.values_list('code', flat=True) if request.user.is_authenticated else []
        return any(role in user_roles for role in allowed_roles)
    except Exception:
        return False

UNFOLD = {
    "SITE_TITLE": "CTUT Blockchain Degree Admin",
    "SITE_HEADER": "Hệ thống Quản lý & Xác minh Văn bằng Blockchain",
    "SITE_SYMBOL": "school",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "DASHBOARD_CALLBACK": "apps.core.views.admin_dashboard_callback",
    "STYLES": [
        lambda request: static("css/animate-ui.css"),
        lambda request: static("css/admin-custom.css"),
    ],
    "SCRIPTS": [
        lambda request: static("js/vendor/gsap.min.js"),
        lambda request: static("js/animate-ui.js"),
    ],
    "COLORS": {
        "primary": {
            "50": "240 247 255",
            "100": "224 239 254",
            "200": "186 224 253",
            "300": "124 197 251",
            "400": "56 167 248",
            "500": "14 140 241",
            "600": "2 111 224",
            "700": "2 88 182",
            "800": "6 75 149",
            "900": "15 23 42",
            "950": "9 13 22",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
                "navigation": [
            {
                "title": _("1. Quy Trình Cấp Phát Văn Bằng"),
                "separator": True,
                "items": [
                    {
                        "title": _("Hồ Sơ Sinh Viên"),
                        "icon": "groups",
                        "link": reverse_lazy("admin:students_student_changelist"),
                        "permission": lambda request: check_menu_role(request, ['officer_a', 'academic_staff', 'officer_b', 'reviewer', 'approver']),
                    },
                    {
                        "title": _("Đợt Xét Tốt Nghiệp"),
                        "icon": "calendar_month",
                        "link": reverse_lazy("admin:graduation_graduationbatch_changelist"),
                        "permission": lambda request: check_menu_role(request, ['officer_a', 'academic_staff', 'officer_b', 'reviewer', 'approver']),
                    },
                    {
                        "title": _("Ký Phát Hành Blockchain"),
                        "icon": "token",
                        "link": reverse_lazy("admin:blockchain_issuancebatch_changelist"),
                        "permission": lambda request: request.user.is_superuser or check_menu_role(request, ['issuer']),
                    },
                    {
                        "title": _("Sổ Cái Văn Bằng Số"),
                        "icon": "workspace_premium",
                        "link": reverse_lazy("admin:degrees_degree_changelist"),
                        "permission": lambda request: request.user.is_superuser or check_menu_role(request, ['officer_a', 'officer_b', 'issuer']),
                    },
                ],
            },
            {
                "title": _("2. Thu Hồi Văn Bằng (4-Eyes)"),
                "separator": True,
                "items": [
                    {
                        "title": _("Yêu Cầu Thu Hồi"),
                        "icon": "gpp_bad",
                        "link": reverse_lazy("admin:revocation_revocationrequest_changelist"),
                        "permission": lambda request: request.user.is_superuser or check_menu_role(request, ['issuer', 'approver', 'officer_b']),
                    },
                    {
                        "title": _("Danh Mục Lý Do Thu Hồi"),
                        "icon": "rule",
                        "link": reverse_lazy("admin:revocation_reasoncode_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                ],
            },
            {
                "title": _("3. Cơ Sở Đào Tạo & Nhập Liệu"),
                "separator": True,
                "items": [
                    {
                        "title": _("Khoa Đào Tạo"),
                        "icon": "corporate_fare",
                        "link": reverse_lazy("admin:academic_faculty_changelist"),
                        "permission": lambda request: check_menu_role(request, ['officer_a', 'academic_staff']),
                    },
                    {
                        "title": _("Ngành Đào Tạo"),
                        "icon": "school",
                        "link": reverse_lazy("admin:academic_major_changelist"),
                        "permission": lambda request: check_menu_role(request, ['officer_a', 'academic_staff']),
                    },
                    {
                        "title": _("Loại Văn Bằng"),
                        "icon": "category",
                        "link": reverse_lazy("admin:academic_degreetype_changelist"),
                        "permission": lambda request: check_menu_role(request, ['officer_a', 'academic_staff']),
                    },
                    {
                        "title": _("Lịch Sử Import Excel"),
                        "icon": "upload_file",
                        "link": reverse_lazy("admin:students_importbatch_changelist"),
                        "permission": lambda request: check_menu_role(request, ['officer_a', 'academic_staff']),
                    },
                ],
            },
            {
                "title": _("4. Phân Quyền & Kiểm Toán"),
                "separator": True,
                "items": [
                    {
                        "title": _("Quản Lý Người Dùng & Ví"),
                        "icon": "manage_accounts",
                        "link": reverse_lazy("admin:accounts_user_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("Vai Trò Hệ Thống"),
                        "icon": "shield",
                        "link": reverse_lazy("admin:accounts_role_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("Nhật Ký Kiểm Toán (Audit)"),
                        "icon": "history",
                        "link": reverse_lazy("admin:audit_auditlog_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("Nhật Ký Tra Cứu Công Khai"),
                        "icon": "fact_check",
                        "link": reverse_lazy("admin:verification_verificationlog_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                ],
            },
            {
                "title": _("5. Cổng Báo Cáo & Dịch Vụ"),
                "separator": True,
                "items": [
                    {
                        "title": _("Dashboard Báo Cáo"),
                        "icon": "analytics",
                        "link": "/report/",
                        "permission": lambda request: request.user.is_superuser or check_menu_role(request, ['issuer', 'admin']),
                    },
                    {
                        "title": _("Cổng Tra Cứu Công Khai"),
                        "icon": "travel_explore",
                        "link": "/",
                        "active": lambda request: False,
                    },
                    {
                        "title": _("Cổng Sinh Viên (Portal)"),
                        "icon": "account_circle",
                        "link": reverse_lazy("student_portal:dashboard"),
                    },
                ],
            },
        ],
    },
}
