import pandas as pd
import math
from django.db import transaction
from .models import ImportBatch, ImportBatchItem, Student
from apps.academic.models import Major

def process_student_import_logic(batch_id, file_path):
    """
    Hàm xử lý đọc file Excel và tạo ImportBatchItem cho từng dòng (UC-02).
    """
    batch = ImportBatch.objects.get(id=batch_id)
    
    try:
        # Đọc file Excel, ép kiểu tất cả về chuỗi để dễ xử lý, bỏ qua các dòng trống
        df = pd.read_excel(file_path, dtype=str).dropna(how='all')
        
        # 1. BỘ TỪ ĐIỂN DỊCH TÊN CỘT (VIỆT -> ANH)
        column_mapping = {
            'Mã SV': 'student_code',
            'Họ và Tên': 'full_name',
            'Ngày Sinh': 'date_of_birth',
            'Giới Tính': 'gender',
            'CCCD': 'national_id',
            'Email': 'email',
            'SĐT': 'phone_number',
            'Mã Khoa': 'faculty_code',
            'Mã Ngành': 'major_code',
            'Năm Nhập Học': 'enrollment_year',
            'Xếp Loại': 'classification'
        }
        # Thực hiện đổi tên cột ngay sau khi đọc file
        df.rename(columns=column_mapping, inplace=True)
        
    except Exception as e:
        batch.errors += 1
        batch.save()
        return False, f"Không thể đọc file: {str(e)}"

    inserted_count = 0
    updated_count = 0
    error_count = 0
    
    # Lấy danh sách mã ngành hợp lệ từ DB để đối chiếu nhanh
    valid_majors = set(Major.objects.filter(is_active=True).values_list('code', flat=True))
    
    items_to_create = []

    # Quét qua từng dòng trong file Excel
    for index, row in df.iterrows():
        row_num = index + 2  # Bù dòng header và index bắt đầu từ 0
        
        # 2. ĐÃ ĐỔI TÊN Ở TRÊN NÊN CHỖ NÀY LẤY BẰNG TÊN TIẾNG ANH
        student_code = str(row.get('student_code', '')).strip()
        full_name = str(row.get('full_name', '')).strip()
        major_code = str(row.get('major_code', '')).strip()
        
        # 1. Bắt lỗi: Thiếu dữ liệu bắt buộc
        if not student_code or student_code == 'nan':
            items_to_create.append(ImportBatchItem(
                import_batch=batch, row_number=row_num, student_code='UNKNOWN',
                action='ERROR', error_message="Thiếu Mã SV"
            ))
            error_count += 1
            continue
            
        if not full_name or full_name == 'nan':
            items_to_create.append(ImportBatchItem(
                import_batch=batch, row_number=row_num, student_code=student_code,
                action='ERROR', error_message="Thiếu Họ và Tên"
            ))
            error_count += 1
            continue

        # 2. Bắt lỗi: Mã ngành không tồn tại trong DB
        if major_code not in valid_majors:
            items_to_create.append(ImportBatchItem(
                import_batch=batch, row_number=row_num, student_code=student_code,
                action='ERROR', error_message=f"Mã ngành '{major_code}' không hợp lệ"
            ))
            error_count += 1
            continue

        # Đóng gói dữ liệu mới để chuẩn bị lưu
        new_data = {
            'full_name': full_name,
            'date_of_birth': str(row.get('date_of_birth', '')),
            'major_code': major_code,
            'classification': str(row.get('classification', ''))
        }

        # 3. Phân loại INSERT hay UPDATE
        student_exists = Student.objects.filter(student_code=student_code).first()
        
        if student_exists:
            # Nếu SV đã có: Lưu lại giá trị cũ để Rollback
            old_data = {
                'full_name': student_exists.full_name,
                'date_of_birth': str(student_exists.date_of_birth),
                'major_code': student_exists.major.code if student_exists.major else '',
                # Tạm lưu classification vào note hoặc cấu trúc khác
            }
            items_to_create.append(ImportBatchItem(
                import_batch=batch, row_number=row_num, student_code=student_code,
                action='UPDATE', old_value=old_data, new_value=new_data
            ))
            updated_count += 1
        else:
            # Sinh viên mới tinh
            items_to_create.append(ImportBatchItem(
                import_batch=batch, row_number=row_num, student_code=student_code,
                action='INSERT', old_value=None, new_value=new_data
            ))
            inserted_count += 1

    # Lưu toàn bộ chi tiết import vào Database bằng 1 lệnh duy nhất (Atomic)
    with transaction.atomic():
        ImportBatchItem.objects.bulk_create(items_to_create)
        
        # Cập nhật tổng kết vào đợt Import
        batch.inserted = inserted_count
        batch.updated = updated_count
        batch.errors = error_count
        batch.save()

    return True, "Kiểm tra dữ liệu hoàn tất. Chờ xác nhận ghi vào DB."