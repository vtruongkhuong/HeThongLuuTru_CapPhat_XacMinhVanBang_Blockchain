from django.urls import path
from . import views

app_name = 'reporting'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('api/stats/', views.stats_api, name='stats_api'),
    path('export/csv/', views.export_degrees_csv, name='export_csv'),
    path('so-goc/excel/', views.export_so_goc_excel_view, name='so_goc_excel'),
    path('so-goc/pdf/', views.export_so_goc_pdf_view, name='so_goc_pdf'),
]