from django.db.models import Count, Sum
from apps.students.models import Student, ImportBatch
from apps.academic.models import Faculty, Major
from apps.degrees.models import Degree
from apps.blockchain.models import BlockchainTransaction
from apps.verification.models import VerificationLog

def get_dashboard_stats():
    """Trích xuất dữ liệu tổng quan cho Dashboard"""
    
    # 1. Các chỉ số cơ bản
    total_students = Student.objects.count()
    total_faculties = Faculty.objects.count()
    total_majors = Major.objects.count()

    # 2. Các chỉ số nâng cao (Executive Metrics)
    try:
        total_verifications = VerificationLog.objects.count()
        
        # Giao dịch blockchain thất bại
        failed_transactions = BlockchainTransaction.objects.filter(status='failed').count()
        
        # Số văn bằng đã cấp
        total_issued_degrees = Degree.objects.filter(status='ISSUED').count()
        
        # Tỷ lệ Import lỗi (Tính theo số đợt có phát sinh dòng lỗi)
        total_batches = ImportBatch.objects.count()
        failed_batches = ImportBatch.objects.filter(errors__gt=0).count()
        import_error_rate = round((failed_batches / total_batches * 100), 1) if total_batches > 0 else 0
        
    except Exception as e:
        print(f"Lỗi truy vấn metrics nâng cao: {e}")
        total_verifications = failed_transactions = import_error_rate = total_issued_degrees = 0

    return {
        'total_students': total_students,
        'total_faculties': total_faculties,
        'total_majors': total_majors,
        'total_issued_degrees': total_issued_degrees,
        'total_verifications': total_verifications,
        'failed_transactions': failed_transactions,
        'import_error_rate': import_error_rate,
        # Lấy 5 đợt import gần nhất
        'recent_imports': ImportBatch.objects.select_related('imported_by').order_by('-created_at')[:5]
    }

def get_chart_data():
    """Trích xuất dữ liệu cho 3 biểu đồ từ Database"""
    
    # 1. Biểu đồ tròn: Tỷ lệ sinh viên theo Khoa
    try:
        # Truy vấn trực tiếp vào khóa ngoại faculty
        fac_stats = Student.objects.values('faculty__name').annotate(count=Count('id'))
        faculty_labels = [item['faculty__name'] or 'Chưa phân khoa' for item in fac_stats]
        faculty_data = [item['count'] for item in fac_stats]
    except Exception:
        faculty_labels, faculty_data = [], []

    # 2. Biểu đồ đường: Tiến độ nhập liệu 
    # (Tạm thời giữ mảng cứng cho các tháng trước, gán dữ liệu thật của tháng hiện tại)
    import_labels = ['Tháng 5', 'Tháng 6', 'Tháng 7', 'Tháng 8', 'Tháng 9', 'Tháng 10']
    try:
        current_students = Student.objects.count()
        import_data = [0, 0, 0, 0, 0, current_students] 
    except Exception:
        import_data = []

    # 3. Biểu đồ tròn: Trạng thái Văn bằng
    try:
        degree_stats = Degree.objects.values('status').annotate(count=Count('id'))
        
        # Map chuẩn với STATUS_CHOICES trong Degree model
        status_map = {
            'DRAFT': 'Nháp',
            'GENERATED': 'Đã tạo PDF',
            'REVIEWED': 'Đã kiểm tra',
            'APPROVED': 'Đã duyệt',
            'ISSUANCE_PENDING': 'Chờ phát hành',
            'ISSUED': 'Đã cấp',
            'REVOKED': 'Đã thu hồi'
        }
        
        degree_labels = []
        degree_data = []
        for item in degree_stats:
            code = item['status']
            degree_labels.append(status_map.get(code, code))
            degree_data.append(item['count'])
            
        if not degree_labels:
             degree_labels = ['Chưa có văn bằng']
             degree_data = [1]
             
    except Exception as e:
        print(f"Lỗi truy vấn biểu đồ văn bằng: {e}")
        degree_labels, degree_data = [], []

    return {
        'faculty': {'labels': faculty_labels, 'data': faculty_data},
        'imports': {'labels': import_labels, 'data': import_data},
        'degrees': {'labels': degree_labels, 'data': degree_data},
    }