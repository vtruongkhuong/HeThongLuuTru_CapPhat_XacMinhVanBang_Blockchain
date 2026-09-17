from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from apps.core.views import dashboard_view
urlpatterns = [
    path('', dashboard_view, name='dashboard'),
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
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
