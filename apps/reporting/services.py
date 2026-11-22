import unicodedata
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncDate, ExtractYear
from apps.students.models import Student, ImportBatch
from apps.academic.models import Faculty, Major
from apps.degrees.models import Degree
from apps.blockchain.models import BlockchainTransaction
from apps.verification.models import VerificationLog


def get_dashboard_stats():
    """Trích xuất dữ liệu tổng quan cho các thẻ thống kê trên Dashboard"""
    total_students = Student.objects.count()
    total_faculties = Faculty.objects.count()
    total_majors = Major.objects.count()
    total_issued_degrees = Degree.objects.filter(status='ISSUED').count()
    total_verifications = VerificationLog.objects.count()
    failed_transactions = BlockchainTransaction.objects.filter(status='failed').count()

    total_batches = ImportBatch.objects.count()
    failed_batches = ImportBatch.objects.filter(errors__gt=0).count()
    import_error_rate = round((failed_batches / total_batches * 100), 1) if total_batches > 0 else 0

    return {
        'total_students': total_students,
        'total_faculties': total_faculties,
        'total_majors': total_majors,
        'total_issued_degrees': total_issued_degrees,
        'total_verifications': total_verifications,
        'failed_transactions': failed_transactions,
        'import_error_rate': import_error_rate,
        'recent_imports': ImportBatch.objects.select_related('imported_by').order_by('-created_at')[:5],
    }


def get_chart_data():
    """
    [BƯỚC 1] Trích xuất dữ liệu cho 3 biểu đồ Chart.js thực tế và các biểu đồ bổ trợ:
    - degrees_by_year: Số lượng văn bằng cấp phát (ISSUED) qua các năm
    - degrees_by_type: Phân bố số lượng văn bằng theo 4 nhóm loại chính
    - verify_by_day: Tần suất tra cứu/xác minh trong 30 ngày gần nhất
    """
    # ── 1. degrees_by_year: Số VB cấp mỗi năm (Bar Chart) ─────────────────────
    # Query: Degree.objects.filter(status='ISSUED').values(year=ExtractYear('issue_date')).annotate(c=Count('id'))
    year_stats = Degree.objects.filter(status='ISSUED')\
        .values(year=ExtractYear('issue_date'))\
        .annotate(c=Count('id'))
    year_map = {item['year']: item['c'] for item in year_stats if item['year']}

    current_year = timezone.now().year
    year_labels = [str(y) for y in range(current_year - 4, current_year + 1)] # ['2022', '2023', '2024', '2025', '2026']
    degrees_by_year_data = [year_map.get(int(y), 0) for y in year_labels]

    degrees_by_year = {
        'labels': year_labels,
        'data': degrees_by_year_data,
    }

    # ── 2. degrees_by_type: Số lượng mỗi loại VB (Doughnut / Pie Chart) ───────
    # Query: Degree.objects.filter(status='ISSUED').values('degree_type__code').annotate(c=Count('id'))
    type_stats = Degree.objects.filter(status='ISSUED')\
        .values('degree_type__code', 'degree_type__name')\
        .annotate(c=Count('id'))

    type_counts = {'Kỹ sư': 0, 'Cử nhân': 0, 'TH Văn phòng': 0, 'CNTT': 0}
    type_code_map = {
        'KS': 'Kỹ sư',
        'CN': 'Cử nhân',
        'THVP': 'TH Văn phòng',
        'CC_THVP': 'TH Văn phòng',
        'CNTT': 'CNTT',
        'CC_CNTT': 'CNTT',
    }
    for item in type_stats:
        code = (item.get('degree_type__code') or '').strip()
        name = (item.get('degree_type__name') or '').strip()
        label = type_code_map.get(code)
        if not label:
            if 'Kỹ sư' in name or 'KS' in code:
                label = 'Kỹ sư'
            elif 'Cử nhân' in name or 'CN' in code:
                label = 'Cử nhân'
            elif 'Văn phòng' in name or 'THVP' in code:
                label = 'TH Văn phòng'
            elif 'CNTT' in code or 'Công nghệ thông tin' in name:
                label = 'CNTT'
            else:
                label = name or 'Khác'
        type_counts[label] = type_counts.get(label, 0) + item['c']

    standard_types = ['Kỹ sư', 'Cử nhân', 'TH Văn phòng', 'CNTT']
    degrees_by_type = {
        'labels': standard_types,
        'data': [type_counts.get(k, 0) for k in standard_types],
    }

    # ── 3. verify_by_day: Số lần verify mỗi ngày trong 30 ngày (Line Chart) ───
    # Query: VerificationLog.objects.filter(created_at__gte=30 ngày trước).values(day=TruncDate('created_at')).annotate(c=Count('id'))
    today = timezone.now().date()
    start_date_30 = today - timedelta(days=29)
    daily_stats = VerificationLog.objects.filter(created_at__date__gte=start_date_30)\
        .annotate(day=TruncDate('created_at'))\
        .values('day')\
        .annotate(c=Count('id'))
    daily_map_30 = {item['day']: item['c'] for item in daily_stats if item['day']}

    verify_labels = []
    verify_data = []
    for i in range(30):
        d = start_date_30 + timedelta(days=i)
        verify_labels.append(d.strftime('%d/%m'))
        verify_data.append(daily_map_30.get(d, 0))

    verify_by_day = {
        'labels': verify_labels,
        'data': verify_data,
    }

    # ── Dữ liệu bổ trợ & tương thích ngược ──────────────────────────────────
    # Phân bố trạng thái văn bằng
    degree_stats = Degree.objects.values('status').annotate(count=Count('id'))
    status_map = {
        'DRAFT': 'Nháp',
        'PENDING': 'Chờ duyệt',
        'GENERATED': 'Đã tạo PDF',
        'REVIEWED': 'Đã kiểm tra',
        'APPROVED': 'Đã duyệt',
        'ISSUANCE_PENDING': 'Chờ phát hành',
        'ISSUED': 'Đã phát hành',
        'REVOKED': 'Đã thu hồi',
    }
    degree_labels = [status_map.get(item['status'], item['status']) for item in degree_stats]
    degree_data = [item['count'] for item in degree_stats]

    return {
        'degrees_by_year': degrees_by_year,
        'degrees_by_type': degrees_by_type,
        'verify_by_day': verify_by_day,
        # Tương thích ngược:
        'degree_types': degrees_by_type,
        'degrees_status': {'labels': degree_labels, 'data': degree_data},
        'daily_verifications': verify_by_day,
    }