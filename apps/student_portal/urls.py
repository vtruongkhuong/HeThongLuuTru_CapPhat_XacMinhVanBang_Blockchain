from django.urls import path
from . import views

app_name = 'student_portal'

urlpatterns = [
    # Trang Dashboard Cổng Sinh viên
    path('dashboard/', views.student_dashboard, name='dashboard'),

    # Trang cập nhật thông tin hồ sơ
    path('cap-nhat-ho-so/', views.update_profile_view, name='profile_update'),

    # Tải & Xem trước file PDF văn bằng / chứng chỉ
    path('tai-van-bang/', views.download_degree_pdf, name='download_pdf'),
    path('tai-van-bang/<int:degree_id>/', views.download_degree_pdf, name='download_pdf_by_id'),
    path('xem-truoc/<int:degree_id>/', views.preview_degree_pdf, name='preview_pdf'),

    # Tải gói xác minh độc lập (JSON Verification Package)
    path('tai-goi-xac-minh/<int:degree_id>/', views.download_verification_package, name='download_verification_package'),
]
