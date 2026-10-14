from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.core.exceptions import PermissionDenied

from apps.students.models import Student, ImportBatch
from apps.academic.models import Faculty, Major
from apps.reporting.services import get_dashboard_stats, get_chart_data

# --- HÀM 1: CHUYÊN ĐIỀU HƯỚNG KHI VỪA ĐĂNG NHẬP ---
@login_required
def dashboard_view(request):
    """Giữ nguyên tên cũ để khỏi sửa LOGIN_REDIRECT_URL. Nhưng giờ nó chỉ để đá người dùng đi nơi khác."""
    user = request.user

    if not user.is_staff and not user.is_superuser:
        return redirect('accounts:profile')

    if user.is_staff and not user.is_superuser:
        role_codes = user.roles.values_list('code', flat=True)

        if 'academic_staff' in role_codes or 'officer_a' in role_codes:
            return redirect('admin:students_importbatch_changelist')
        elif 'reviewer' in role_codes or 'approver' in role_codes or 'officer_b' in role_codes:
            return redirect('admin:graduation_graduationbatch_changelist')
        elif 'issuer' in role_codes:
            return redirect('admin:blockchain_issuancebatch_changelist') 

    # ĐÁ SUPER ADMIN & LÃNH ĐẠO VÀO THẲNG GIAO DIỆN ADMIN LUÔN
    return redirect('/admin/')


# --- HÀM 2: CHUYÊN HIỂN THỊ BÁO CÁO ---
@login_required
def report_view(request):
    user = request.user
    
    # 1. Chặn sinh viên (Cấp user thường)
    if not user.is_staff and not user.is_superuser:
        return redirect('accounts:profile')

    # 2. Chặn Cán bộ vận hành (Chỉ Admin và Issuer được phép xem)
    if not user.is_superuser:
        role_codes = user.roles.values_list('code', flat=True)
        if 'admin' not in role_codes and 'issuer' not in role_codes:
            # Ném thẳng lỗi 403 Forbidden nếu cố tình gõ URL truy cập
            raise PermissionDenied("Bạn không có quyền xem báo cáo thống kê của hệ thống.")

    # 3. Lấy dữ liệu (Đã xóa dòng gán recent_imports thừa)
    stats = get_dashboard_stats()
    chart_data = get_chart_data()

    context = {
        'stats': stats,
        'chart_data': chart_data
    }
    return render(request, 'dashboard.html', context)