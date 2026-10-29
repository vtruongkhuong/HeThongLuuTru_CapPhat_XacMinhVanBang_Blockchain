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
        return redirect('landing')

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


def custom_404_view(request, exception=None):
    """[N7] Trang báo lỗi 404 tùy biến chuẩn nhận diện thương hiệu"""
    return render(request, '404.html', status=404)


def custom_500_view(request):
    """[N7] Trang báo lỗi 500 tùy biến chuẩn nhận diện thương hiệu"""
    return render(request, '500.html', status=500)


def animate_ui_demo_view(request):
    """[Animate UI Showcase] Trang trải nghiệm hiệu ứng tương tác cao cấp Animate UI"""
    return render(request, 'animate_ui_demo.html')



def admin_dashboard_callback(request, context):
    """
    [Apple Design Command Center] Callback chuẩn Unfold Admin
    Cung cấp số liệu thời gian thực, chỉ số KPI và danh sách đợt tốt nghiệp cần xử lý.
    """
    try:
        from apps.students.models import Student
        from apps.graduation.models import GraduationBatch
        from apps.degrees.models import Degree
        from apps.blockchain.models import IssuanceBatch

        total_degrees = Degree.objects.filter(status='ISSUED').count()
        total_students = Student.objects.count()
        pending_batches_count = GraduationBatch.objects.filter(status__in=['submitted', 'reviewed']).count()
        recent_batches = list(GraduationBatch.objects.select_related('faculty', 'created_by').order_by('-created_at')[:5])
        total_issuance = IssuanceBatch.objects.count()

        context.update({
            "kpis": [
                {
                    "title": "Văn bằng trên chuỗi (ISSUED)",
                    "metric": total_degrees,
                    "icon": "workspace_premium",
                    "badge": "Active On-Chain",
                    "badge_color": "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20",
                    "link": "/admin/degrees/degree/?status__exact=ISSUED",
                },
                {
                    "title": "Đợt tốt nghiệp chờ duyệt",
                    "metric": pending_batches_count,
                    "icon": "pending_actions",
                    "badge": "Cần phê duyệt" if pending_batches_count > 0 else "Đã duyệt hết",
                    "badge_color": "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20" if pending_batches_count > 0 else "bg-gray-500/10 text-gray-500 border border-gray-500/20",
                    "link": "/admin/graduation/graduationbatch/?status__exact=submitted",
                },
                {
                    "title": "Hồ sơ sinh viên",
                    "metric": total_students,
                    "icon": "groups",
                    "badge": "Toàn trường",
                    "badge_color": "bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20",
                    "link": "/admin/students/student/",
                },
                {
                    "title": "Đợt phát hành Blockchain",
                    "metric": total_issuance,
                    "icon": "token",
                    "badge": "Smart Contract v2",
                    "badge_color": "bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20",
                    "link": "/admin/blockchain/issuancebatch/",
                },
            ],
            "recent_batches": recent_batches,
        })
    except Exception as e:
        pass
    return context
