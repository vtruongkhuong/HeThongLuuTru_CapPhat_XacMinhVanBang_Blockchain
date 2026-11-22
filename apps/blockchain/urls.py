from django.urls import path
from . import views

app_name = 'blockchain'

urlpatterns = [
    path('ipfs/<str:cid>/', views.ipfs_viewer_view, name='ipfs_viewer'),
    path('transactions/', views.transaction_list_view, name='transaction_list'),
]
