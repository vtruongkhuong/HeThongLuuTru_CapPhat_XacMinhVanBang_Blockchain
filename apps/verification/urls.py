from django.urls import path
from . import views

app_name = 'verification'

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('tracuu/', views.public_verify_view, name='public_verify'),
    path('tracuu-tam-thoi/', views.verify_temp_cert_view, name='verify_temp_cert'),
    path('doanh-nghiep/', views.employer_batch_verify_view, name='employer_batch_verify'),
    path('chung-thuc-pdf/<str:degree_id>/', views.download_verification_cert_pdf, name='download_verification_cert_pdf'),
]