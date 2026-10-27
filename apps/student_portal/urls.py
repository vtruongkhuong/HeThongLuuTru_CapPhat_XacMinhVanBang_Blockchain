from django.urls import path
from . import views

app_name = 'student_portal'

urlpatterns = [
    # Trang Dashboard Cổng Sinh viên
    path('dashboard/', views.student_dashboard, name='dashboard'),

    # Trang cập nhật thông tin hồ sơ
    path('cap-nhat-ho-so/', views.update_profile_view, name='profile_update'),

    # Tải file PDF văn bằng / chứng chỉ
    path('tai-van-bang/', views.download_degree_pdf, name='download_pdf'),
    path('tai-van-bang/<int:degree_id>/', views.download_degree_pdf, name='download_pdf_by_id'),
]
