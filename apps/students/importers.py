"""
Logic xử lý import file Excel sinh viên.
Hỗ trợ INSERT, UPDATE, SKIP, ERROR và lưu old_value để Rollback.
"""
import hashlib
import pandas as pd
from datetime import datetime
from django.db import transaction
from django.forms.models import model_to_dict

from apps.academic.models import Major
from apps.graduation.models import GraduationBatch
from apps.audit.services import log_action # Giả định bạn có model này
from .models import Student, ImportBatch, ImportBatchItem

def calculate_file_hash(file_obj):
    """Tính SHA-256 hash của file upload."""
    sha256_hash = hashlib.sha256()
    # Read and update hash in chunks of 4K
    for byte_block in iter(lambda: file_obj.read(4096), b""):
        sha256_hash.update(byte_block)
    file_obj.seek(0) # Reset file pointer for later reading
    return sha256_hash.hexdigest()

def _read_gpa(row):
    for key in ('gpa', 'gpa_score', 'điểm gpa'):
        raw = row.get(key)
        if pd.notna(raw) and str(raw).strip() != '':
            try:
                gpa = float(str(raw).strip().replace(',', '.'))
                if 0 <= gpa <= 4:
                    return gpa
                raise ValueError(f"GPA phải từ 0 đến 4: '{raw}'")
            except ValueError:
                raise ValueError(f"GPA không hợp lệ: '{raw}'")
    return None

def _read_dob(row):
    for key in ('ngày sinh', 'date_of_birth', 'ngay sinh'):
        raw = row.get(key)
        if pd.notna(raw) and str(raw).strip() != '':
            if hasattr(raw, 'date'):
                return raw.date()
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
                try:
                    return datetime.strptime(str(raw).strip()[:10], fmt).date()
                except ValueError:
                    continue
            raise ValueError(f"Không đọc được ngày sinh: '{raw}'")
    return None

def process_excel_import(excel_file, batch_id, user):
    """
    Xử lý file Excel, tạo ImportBatch và các ImportBatchItem.
    """
    file_hash = calculate_file_hash(excel_file)
    
    # Kiểm tra chống nạp trùng file
    if ImportBatch.objects.filter(file_hash=file_hash, batch_id=batch_id).exclude(status__in=['rolled_back', 'failed']).exists():
        raise Exception("File này đã được import cho đợt tốt nghiệp này (Trùng File Hash).")

    batch_obj = GraduationBatch.objects.get(pk=batch_id)
    
    # Đọc file bằng Pandas
    try:
        df = pd.read_excel(excel_file)
        df.columns = df.columns.str.strip().str.lower()
    except Exception as e:
        raise Exception(f"Không thể đọc file Excel. Chi tiết: {str(e)}")

    import_batch = ImportBatch.objects.create(
        batch=batch_obj,
        file_name=excel_file.name,
        file_hash=file_hash,
        imported_by=user,
        mode='PARTIAL'
    )

    inserted_count = updated_count = skipped_count = error_count = 0

    with transaction.atomic():
        for index, row in df.iterrows():
            row_num = index + 2 # Header là dòng 1 trong Excel
            mssv = str(row.get('mã sv', row.get('student_code', ''))).strip()
            
            if not mssv or mssv == 'nan':
                skipped_count += 1
                ImportBatchItem.objects.create(
                    import_batch=import_batch, row_number=row_num, student_code='UNKNOWN',
                    action='SKIP', error_message="Dòng trống hoặc thiếu Mã SV."
                )
                continue

            try:
                ho_ten = str(row.get('họ tên', row.get('full_name', ''))).strip()
                ma_nganh = str(row.get('mã ngành', row.get('major_code', ''))).strip()
                email_sv = str(row.get('email', '')).strip()
                
                # Loại văn bằng/chứng chỉ (CN, KS, THVP, CNTT) - Hỗ trợ cho H6 sau này
                loai_van_bang = str(row.get('loại bằng', row.get('degree_type', ''))).strip()

                if not email_sv or email_sv == 'nan':
                    raise ValueError("Thiếu dữ liệu: Cột Email là bắt buộc.")
                
                major_obj = Major.objects.filter(code=ma_nganh).first()
                if not major_obj:
                    raise ValueError(f"Không tìm thấy mã ngành: {ma_nganh}")

                gpa_val = _read_gpa(row)
                dob_val = _read_dob(row)

                defaults = {
                    'full_name': ho_ten,
                    'email': email_sv,
                    'major': major_obj,
                    'faculty': major_obj.faculty,
                }
                if gpa_val is not None:
                    defaults['gpa_score'] = gpa_val
                if dob_val is not None:
                    defaults['date_of_birth'] = dob_val

                # Kiểm tra Update hay Insert để lưu old_value
                student = Student.objects.filter(student_code=mssv).first()
                
                old_val_json = None
                new_val_json = {
                    'full_name': ho_ten,
                    'email': email_sv,
                    'major': ma_nganh,
                    'gpa': gpa_val,
                    'date_of_birth': str(dob_val) if dob_val else None,
                    'degree_type': loai_van_bang # Lưu loại văn bằng để H6 dùng
                }

                if student:
                    # Chẩn bị update
                    old_val_json = model_to_dict(student, fields=['full_name', 'email', 'major', 'gpa_score', 'date_of_birth'])
                    # model_to_dict trả về ID cho khoá ngoại, ta cần convert lại cho dễ đọc nếu cần
                    old_val_json['major'] = student.major.code if student.major else None
                    if isinstance(old_val_json['date_of_birth'], datetime):
                       old_val_json['date_of_birth'] = str(old_val_json['date_of_birth'].date())

                    for key, value in defaults.items():
                        setattr(student, key, value)
                    student.save()
                    action_type = 'UPDATE'
                    updated_count += 1
                else:
                    student = Student.objects.create(student_code=mssv, **defaults)
                    action_type = 'INSERT'
                    inserted_count += 1

                ImportBatchItem.objects.create(
                    import_batch=import_batch,
                    row_number=row_num,
                    student_code=mssv,
                    action=action_type,
                    old_value=old_val_json,
                    new_value=new_val_json
                )

            except Exception as row_err:
                error_count += 1
                ImportBatchItem.objects.create(
                    import_batch=import_batch,
                    row_number=row_num,
                    student_code=mssv,
                    action='ERROR',
                    error_message=str(row_err)[:250]
                )

    # Cập nhật tổng kết
    import_batch.inserted = inserted_count
    import_batch.updated = updated_count
    import_batch.skipped = skipped_count
    import_batch.errors = error_count
    import_batch.save()

    try:
        log_action(
            actor=user,
            action='IMPORT_EXCEL',
            entity_type='ImportBatch',
            entity_id=str(import_batch.id),
            new={
                'file_name': excel_file.name,
                'file_hash': file_hash,
                'batch_id': batch_id,
                'inserted': inserted_count,
                'updated': updated_count,
                'skipped': skipped_count,
                'errors': error_count
            }
        )
    except Exception as log_err:
        print(f'[AuditLog Error] {log_err}')

    return import_batch