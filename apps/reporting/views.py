import csv
from datetime import date
from django.utils import timezone
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied

from .services import get_dashboard_stats, get_chart_data
from apps.degrees.models import Degree
from apps.verification.models import VerificationLog


def stats_api(request):
    """
    [BƯỚC 2] View AJAX trả JSON thống kê cho 3 biểu đồ Chart.js, 4 thẻ KPI và Widget Hiệu quả
    Endpoint: /reporting/api/stats/
    """
    today = timezone.now().date()
    stats = get_dashboard_stats()
    return JsonResponse({
        'charts': get_chart_data(),
        'kpi': {
            'total_issued': Degree.objects.filter(status='ISSUED').count(),
            'pending':      Degree.objects.filter(status__in=['DRAFT', 'REVIEWED', 'APPROVED']).count(),
            'revoked':      Degree.objects.filter(status='REVOKED').count(),
            'verify_today': VerificationLog.objects.filter(created_at__date=today).count(),
        },
        'efficiency_metrics': stats.get('efficiency_metrics', {}),
    })


@staff_member_required
def dashboard_view(request):
    """View hiển thị trang Dashboard Báo cáo"""
    today = timezone.now().date()
    context = {
        'title': 'Dashboard Thống Kê & Báo Cáo',
        'stats': get_dashboard_stats(),
        'charts': get_chart_data(),
        'kpi': {
            'total_issued': Degree.objects.filter(status='ISSUED').count(),
            'pending':      Degree.objects.filter(status__in=['DRAFT', 'REVIEWED', 'APPROVED']).count(),
            'revoked':      Degree.objects.filter(status='REVOKED').count(),
            'verify_today': VerificationLog.objects.filter(created_at__date=today).count(),
        }
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


@staff_member_required
def export_so_goc_excel_view(request):
    """Xuất file Excel Sổ gốc cấp phát văn bằng chuẩn Thông tư 21/2019/TT-BGDĐT"""
    from .so_goc_service import generate_so_goc_excel
    from apps.graduation.models import GraduationBatch
    from apps.audit.services import log_action

    batch_id = request.GET.get('batch_id')
    batch = GraduationBatch.objects.filter(id=batch_id).first() if batch_id else None

    excel_bytes = generate_so_goc_excel(batch=batch, batch_id=batch_id)

    batch_slug = f"_{batch.id}" if batch else "_ToanTruong"
    filename = f"SoGoc_CapPhat_VanBang{batch_slug}.xlsx"

    try:
        log_action(
            actor=request.user,
            action='EXPORT_SO_GOC',
            entity_type='GraduationBatch',
            entity_id=str(batch.id) if batch else 'ALL',
            new={'format': 'EXCEL', 'filename': filename}
        )
    except Exception:
        pass

    response = HttpResponse(
        excel_bytes,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@staff_member_required
def export_so_goc_pdf_view(request):
    """Xuất file PDF Sổ gốc cấp phát văn bằng chuẩn Thông tư 21/2019/TT-BGDĐT"""
    from .so_goc_service import generate_so_goc_pdf
    from apps.graduation.models import GraduationBatch
    from apps.audit.services import log_action

    batch_id = request.GET.get('batch_id')
    batch = GraduationBatch.objects.filter(id=batch_id).first() if batch_id else None

    pdf_bytes = generate_so_goc_pdf(batch=batch, batch_id=batch_id)
    if not pdf_bytes:
        return HttpResponse("Lỗi khi kết xuất file PDF Sổ gốc.", status=500)

    batch_slug = f"_{batch.id}" if batch else "_ToanTruong"
    filename = f"SoGoc_CapPhat_VanBang{batch_slug}.pdf"

    try:
        log_action(
            actor=request.user,
            action='EXPORT_SO_GOC',
            entity_type='GraduationBatch',
            entity_id=str(batch.id) if batch else 'ALL',
            new={'format': 'PDF', 'filename': filename}
        )
    except Exception:
        pass

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response
