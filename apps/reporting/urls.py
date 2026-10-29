from django.urls import path
from . import views

app_name = 'reporting'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('export/csv/', views.export_degrees_csv, name='export_csv'),
]