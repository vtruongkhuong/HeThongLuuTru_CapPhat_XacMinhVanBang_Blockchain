import unicodedata
from django.db.models import Count
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
    """Trích xuất dữ liệu cho 3 biểu đồ Chart.js"""
    # 1. Phân bố theo Loại văn bằng (Chuẩn hóa Unicode & khoảng trắng để gộp trùng tuyệt đối)
    dt_stats = Degree.objects.values('degree_type__name').annotate(count=Count('id'))
    merged_dt = {}
    display_names = {}
    
    for item in dt_stats:
        raw_name = (item['degree_type__name'] or 'Chưa phân loại').strip()
        norm_key = unicodedata.normalize('NFC', " ".join(raw_name.split())).lower()
        
        merged_dt[norm_key] = merged_dt.get(norm_key, 0) + item['count']
        if norm_key not in display_names or item['count'] > 5:
            display_names[norm_key] = raw_name

    degree_type_labels = [display_names[k] for k in merged_dt.keys()]
    degree_type_data = list(merged_dt.values())

    # 2. Trạng thái Văn bằng
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

    # 3. Kết quả Tra cứu / Xác minh (Cố định thứ tự: Hợp lệ [Xanh] -> Không hợp lệ [Đỏ])
    ver_labels, ver_data = [], []
    try:
        excluded = {
            'id', 'uuid', 'ip_address', 'user_agent', 'created_at', 
            'updated_at', 'timestamp', 'verified_at', 'query', 
            'search_query', 'public_id', 'credential_public_id'
        }
        candidate_fields = [
            f.name for f in VerificationLog._meta.concrete_fields
            if f.name not in excluded and not f.is_relation
        ]
        priority = ['result', 'status', 'verification_status', 'is_valid', 'valid', 'outcome', 'verify_result']
        target_field = next((p for p in priority if p in candidate_fields), candidate_fields[0] if candidate_fields else None)

        if target_field:
            ver_stats = VerificationLog.objects.values(target_field).annotate(count=Count('id'))
            temp_counts = {'Hợp lệ': 0, 'Không hợp lệ': 0}
            
            for item in ver_stats:
                val = item[target_field]
                if isinstance(val, bool):
                    label = 'Hợp lệ' if val else 'Không hợp lệ'
                elif str(val).upper() in ('VALID', 'TRUE', 'SUCCESS', 'HOP_LE', 'HỢP LỆ', '1'):
                    label = 'Hợp lệ'
                elif str(val).upper() in ('INVALID', 'FALSE', 'FAILED', 'REVOKED', 'NOT_FOUND', 'KHONG_HOP_LE', 'KHÔNG HỢP LỆ', '0'):
                    label = 'Không hợp lệ'
                else:
                    label = str(val) if val is not None else 'Khác'
                
                temp_counts[label] = temp_counts.get(label, 0) + item['count']

            for key in ['Hợp lệ', 'Không hợp lệ']:
                if temp_counts.get(key, 0) > 0:
                    ver_labels.append(key)
                    ver_data.append(temp_counts[key])
            for key, val in temp_counts.items():
                if key not in ('Hợp lệ', 'Không hợp lệ') and val > 0:
                    ver_labels.append(key)
                    ver_data.append(val)
    except Exception as e:
        print(f"Lỗi truy vấn VerificationLog: {e}")

    return {
        'degree_types': {'labels': degree_type_labels, 'data': degree_type_data},
        'degrees_status': {'labels': degree_labels, 'data': degree_data},
        'verifications': {'labels': ver_labels, 'data': ver_data},
    }