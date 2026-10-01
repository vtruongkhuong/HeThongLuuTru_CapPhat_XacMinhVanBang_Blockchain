from django.urls import path
from . import views

# Khai báo không gian tên (namespace) cho app
app_name = 'student_portal'

urlpatterns = [
    # Trang Dashboard
    path('dashboard/', views.student_dashboard, name='dashboard'),
    
    # Trang cập nhật thông tin hồ sơ
    path('cap-nhat-ho-so/', views.update_profile_view, name='profile_update'),
    
    # Trang tải file PDF văn bằng (cho chức năng trước đó bạn vừa làm)
    path('tai-van-bang/', views.download_degree_pdf, name='download_pdf'),
]