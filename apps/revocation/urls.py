from django.urls import path
from . import views

app_name = 'revocation'

urlpatterns = [
    path('execute/<int:pk>/', views.execute_revocation_metamask_view, name='execute_metamask'),
]