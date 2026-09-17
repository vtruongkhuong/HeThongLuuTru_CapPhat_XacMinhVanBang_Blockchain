import pandas as pd
from django.db import transaction
from .models import ImportBatch, ImportBatchItem, Student
from apps.academic.models import Major

def process_student_import_logic(batch_id, file_path):
    batch = ImportBatch.objects.get(id=batch_id)
    
    try:
        # Đọc Excel và chuyển đổi tên cột
        df = pd.read_excel(file_path, dtype=str).dropna(how='all')
        column_mapping = {
            'Mã SV': 'student_code',
            'Họ và Tên': 'full_name',
            'Ngày Sinh': 'date_of_birth',
            'Mã Khoa': 'faculty_code',
            'Mã Ngành': 'major_code',
            'Năm Nhập Học': 'enrollment_year',
            'Xếp Loại': 'classification'
        }
        df.rename(columns=column_mapping, inplace=True)
    except Exception as e:
        batch.errors += 1
        batch.save()
        return False, f"Không thể đọc file: {str(e)}"

    inserted_count = 0
    updated_count = 0
    error_count = 0
    
    # Lấy từ điển Ngành ra để gán trực tiếp cho Sinh viên
    majors_dict = {m.code: m for m in Major.objects.all()}
    
    items_to_create = []     # Danh sách ghi lịch sử nháp
    students_to_create = []  # Danh sách chèn vào bảng Sinh viên chính thức

    for index, row in df.iterrows():
        row_num = index + 2
        student_code = str(row.get('student_code', '')).strip()
        full_name = str(row.get('full_name', '')).strip()
        major_code = str(row.get('major_code', '')).strip()
        
        # Bỏ qua nếu thiếu dữ liệu cốt lõi
        if not student_code or student_code == 'nan':
            items_to_create.append(ImportBatchItem(import_batch=batch, row_number=row_num, action='ERROR', error_message="Thiếu Mã SV"))
            error_count += 1
            continue
            
        if major_code not in majors_dict:
            items_to_create.append(ImportBatchItem(import_batch=batch, row_number=row_num, action='ERROR', error_message=f"Mã ngành '{major_code}' không hợp lệ"))
            error_count += 1
            continue

        major_obj = majors_dict[major_code]
        student_exists = Student.objects.filter(student_code=student_code).first()
        new_data = {'full_name': full_name, 'major_code': major_code}

        if student_exists:
            # Ghi lịch sử là Cập nhật
            items_to_create.append(ImportBatchItem(import_batch=batch, row_number=row_num, student_code=student_code, action='UPDATE', new_value=new_data))
            
            # CẬP NHẬT THỰC TẾ
            student_exists.full_name = full_name
            student_exists.major = major_obj
            if hasattr(major_obj, 'faculty'):
                student_exists.faculty = major_obj.faculty
            student_exists.save()
            updated_count += 1
            
        else:
            # Ghi lịch sử là Tạo mới
            items_to_create.append(ImportBatchItem(import_batch=batch, row_number=row_num, student_code=student_code, action='INSERT', new_value=new_data))
            
            # TẠO MỚI THỰC TẾ
            new_student = Student(
                student_code=student_code,
                full_name=full_name,
                major=major_obj
            )
            # Tự động gán Khoa dựa theo Ngành
            if hasattr(major_obj, 'faculty'):
                new_student.faculty = major_obj.faculty
            
            # Lưu Năm nhập học nếu có
            enrollment_year = str(row.get('enrollment_year', '')).strip()
            if enrollment_year.isdigit():
                new_student.enrollment_year = int(enrollment_year)
                
            students_to_create.append(new_student)
            inserted_count += 1

    # Đóng gói và gửi tất cả vào Database cùng 1 lúc
    with transaction.atomic():
        ImportBatchItem.objects.bulk_create(items_to_create)
        if students_to_create:
            Student.objects.bulk_create(students_to_create)
            
        batch.inserted = inserted_count
        batch.updated = updated_count
        batch.errors = error_count
        batch.status = 'completed'  # Đánh dấu đã hoàn thành việc Import
        batch.save()

    return True, "Import thành công! Đã ghi dữ liệu vào bảng Sinh Viên."