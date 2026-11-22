from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('verify/<uuid:uuid>/', views.VerifyByUUIDView.as_view(), name='verify_uuid'),
    path('verify/hash/', views.VerifyByHashView.as_view(), name='verify_hash'),
    path('verify/batch/', views.VerifyBatchView.as_view(), name='verify_batch'),
]