import csv
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied

from .services import get_dashboard_stats, get_chart_data
from apps.degrees.models import Degree


@staff_member_required
def dashboard_view(request):
    """View hiển thị trang Dashboard Báo cáo"""
    context = {
        'title': 'Dashboard Thống Kê & Báo Cáo',
        'stats': get_dashboard_stats(),
        'charts': get_chart_data(),
    }
    return render(request, 'dashboard.html', context)


@login_required
def export_degrees_csv(request):
    """Xuất báo cáo CSV - Chỉ cho phép Superuser, Admin và Issuer"""
    user = request.user
    if not user.is_superuser:
        role_codes = user.roles.values_list('code', flat=True) if hasattr(user, 'roles') else []
        if 'admin' not in role_codes and 'issuer' not in role_codes:
            raise PermissionDenied("Bạn không có quyền xuất báo cáo thống kê của hệ thống.")

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="BaoCao_VanBang.csv"'
    response.write('\ufeff'.encode('utf8'))
    writer = csv.writer(response)
    writer.writerow(['MSSV', 'Họ Tên', 'Loại Văn Bằng', 'Ngành Học', 'Trạng Thái', 'Ngày Phát Hành', 'Mã Tra Cứu (Public ID)'])

    degrees = Degree.objects.all().select_related('student', 'degree_type', 'student__major')
    for d in degrees:
        nganh_hoc = d.student.major.name if d.student and d.student.major else "N/A"
        ngay_cap = d.issue_date.strftime('%d/%m/%Y') if d.issue_date else "Chưa cấp"
        writer.writerow([
            d.student.student_code,
            d.student.full_name,
            d.degree_type.name if d.degree_type else "N/A",
            nganh_hoc,
            d.get_status_display(),
            ngay_cap,
            str(d.credential_public_id)
        ])
    return response