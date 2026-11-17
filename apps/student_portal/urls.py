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

    # [Nghĩa - Task 3] Quản lý & Xem Link chia sẻ hồ sơ tạm thời cho Nhà tuyển dụng
    path('tao-link-chia-se/', views.create_share_link, name='create_share_link'),
    path('huy-link-chia-se/<uuid:link_id>/', views.revoke_share_link, name='revoke_share_link'),
    path('chia-se/<str:token>/', views.public_shared_profile_view, name='public_shared_profile'),
]
