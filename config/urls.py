from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.verification import views as verification_views
from apps.blockchain import views as blockchain_views
from apps.core.views import dashboard_view, report_view, custom_404_view, custom_500_view, animate_ui_demo_view
from apps.reporting import views as reporting_views
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # Điều hướng gốc & tương thích ngược cho các template gọi trực tiếp tên URL
    path('', verification_views.landing_view, name='landing'),
    path('tracuu/', verification_views.public_verify_view, name='public_verify'),
    path('tracuu-tam-thoi/', verification_views.verify_temp_cert_view, name='verify_temp_cert'),
    path('doanh-nghiep/', verification_views.employer_batch_verify_view, name='employer_batch_verify'),
    path('doanh-nghiep/mau-excel/', verification_views.download_employer_sample_excel, name='employer_sample_excel_root'),
    path('doanh-nghiep/xuat-excel/', verification_views.export_employer_results_excel_view, name='export_employer_excel_root'),
    path('animate-ui/', animate_ui_demo_view, name='animate_ui_demo'),

    # Route chuẩn có app_name = 'verification' theo yêu cầu N2
    path('verify/', include('apps.verification.urls')),

    # Trạm điều phối và Admin
    path('dashboard/', dashboard_view, name='dashboard'),
    path('admin/blockchain/transactions/', blockchain_views.transaction_list_view, name='admin_blockchain_transactions'),
    path('admin/', admin.site.urls),
    path('report/', report_view, name='report'),

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
    path('reporting/api/stats/', reporting_views.stats_api, name='reporting_api_stats'),
    path('reporting/', reporting_views.dashboard_view, name='reporting_dashboard'),
    path('api/v1/', include('apps.api.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('accounts/', include('allauth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Tuyến đường xem trước trang lỗi khi đang bật DEBUG=True (N7)
    urlpatterns += [
        path('test-404/', custom_404_view, name='test_404'),
        path('test-500/', custom_500_view, name='test_500'),
    ]

# Custom HTTP error handlers (N7)
handler404 = 'apps.core.views.custom_404_view'
handler500 = 'apps.core.views.custom_500_view'
