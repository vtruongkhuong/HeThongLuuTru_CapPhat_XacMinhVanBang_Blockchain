from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.verification import views as verification_views
from apps.core.views import dashboard_view

urlpatterns = [
    # Điều hướng gốc & tương thích ngược cho các template gọi trực tiếp tên URL
    path('', verification_views.landing_view, name='landing'),
    path('tracuu/', verification_views.public_verify_view, name='public_verify'),
    path('tracuu-tam-thoi/', verification_views.verify_temp_cert_view, name='verify_temp_cert'),

    # Route chuẩn có app_name = 'verification' theo yêu cầu N2
    path('verify/', include('apps.verification.urls')),

    # Trạm điều phối và Admin
    path('dashboard/', dashboard_view, name='dashboard'),
    path('admin/', admin.site.urls),

    # Các module hệ thống
    path('accounts/', include('apps.accounts.urls')),
    path('academic/', include('apps.academic.urls')),
    path('students/', include('apps.students.urls')),
    path('graduation/', include('apps.graduation.urls')),
    path('degrees/', include('apps.degrees.urls')),
    path('blockchain/', include('apps.blockchain.urls')),
    path('revocation/', include('apps.revocation.urls')),
    path('portal/', include('apps.student_portal.urls')),
    path('reports/', include('apps.reporting.urls')),
    path('accounts/', include('allauth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)