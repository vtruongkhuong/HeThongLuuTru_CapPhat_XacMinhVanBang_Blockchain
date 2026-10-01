from django.contrib import admin
from django.urls import path, include
from apps.verification import views as verification_views
from django.conf import settings
from django.conf.urls.static import static
from apps.student_portal import views as student_views
from apps.core.views import dashboard_view

urlpatterns = [
   # Trang chủ mặc định hiển thị 3 thẻ bài
    path('', verification_views.landing_view, name='landing'),
    
    # Trang tra cứu mới (đường dẫn /tracuu/)
    path('tracuu/', verification_views.public_verify_view, name='public_verify'),
    
    path('tracuu-tam-thoi/', verification_views.verify_temp_cert_view, name='verify_temp_cert'),
    path('admin/', admin.site.urls),

path('cap-nhat-ho-so/', student_views.update_profile_view, name='profile_update'),
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