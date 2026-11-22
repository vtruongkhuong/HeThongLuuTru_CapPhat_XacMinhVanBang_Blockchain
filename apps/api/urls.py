from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('verify/<uuid:uuid>/', views.VerifyByUUIDView.as_view(), name='verify_uuid'),
    path('verify/hash/', views.VerifyByHashView.as_view(), name='verify_hash'),
    path('verify/batch/', views.VerifyBatchView.as_view(), name='verify_batch'),
    path('degrees/<uuid:uuid>/credential.json', views.DownloadVerifiableCredentialView.as_view(), name='download_vc'),
    path('degrees/<uuid:uuid>/ipfs-upload/', views.IPFSUploadView.as_view(), name='ipfs_upload'),
]
