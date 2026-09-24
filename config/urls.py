from django.contrib import admin
from django.urls import path, include
from apps.verification import views as verification_views
from django.conf import settings
from django.conf.urls.static import static

from apps.core.views import dashboard_view

urlpatterns = [
    # 1. TRANG CHỦ MẶC ĐỊNH LÀ CỔNG TRA CỨU
    path('', verification_views.public_verify_view, name='public_verify'),

    # 2. Đẩy Trạm điều phối vào đường dẫn /dashboard/
    path('dashboard/', dashboard_view, name='dashboard'),
    
    path('admin/', admin.site.urls),

    path('accounts/', include('apps.accounts.urls')),
    path('academic/', include('apps.academic.urls')),
    path('students/', include('apps.students.urls')),
    path('graduation/', include('apps.graduation.urls')),
    path('degrees/', include('apps.degrees.urls')),
    path('blockchain/', include('apps.blockchain.urls')),
    path('revocation/', include('apps.revocation.urls')),
    path('verify/', include('apps.verification.urls')),
    path('portal/', include('apps.student_portal.urls')),
    path('reports/', include('apps.reporting.urls')),
    path('accounts/', include('allauth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)