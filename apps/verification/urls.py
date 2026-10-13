from django.urls import path
from . import views

app_name = 'verification'

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('tracuu/', views.public_verify_view, name='public_verify'),
    path('tracuu-tam-thoi/', views.verify_temp_cert_view, name='verify_temp_cert'),
]