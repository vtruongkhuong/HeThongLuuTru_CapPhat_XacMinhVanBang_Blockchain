from django.urls import path
from . import views

app_name = 'verification'

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('tracuu/', views.public_verify_view, name='public_verify'),
    path('tracuu-tam-thoi/', views.verify_temp_cert_view, name='verify_temp_cert'),
    path('doanh-nghiep/', views.employer_batch_verify_view, name='employer_batch_verify'),
    path('doanh-nghiep/mau-excel/', views.download_employer_sample_excel, name='employer_sample_excel'),
    path('doanh-nghiep/xuat-excel/', views.export_employer_results_excel_view, name='export_employer_results_excel'),
    path('chung-thuc-pdf/<str:degree_id>/', views.download_verification_cert_pdf, name='download_verification_cert_pdf'),
    path('badge/<str:degree_uuid>.svg', views.degree_badge_svg, name='degree_badge_svg'),
    # [Nghĩa - Tech Showcase] Visual Merkle Tree & W3C Verifiable Credentials
    path('merkle-tree/', views.merkle_visualizer_view, name='merkle_visualizer'),
    path('merkle-tree/<str:identifier>/', views.merkle_visualizer_view, name='merkle_visualizer_detail'),
    path('w3c-verifier/', views.w3c_standalone_verifier_view, name='w3c_standalone_verifier'),
    path('w3c-vc/<str:identifier>/', views.export_w3c_vc_json, name='export_w3c_vc'),
]