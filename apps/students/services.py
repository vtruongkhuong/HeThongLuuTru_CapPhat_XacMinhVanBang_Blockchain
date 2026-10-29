import pandas as pd
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import ImportBatch, ImportBatchItem, Student
from apps.academic.models import Major
from apps.degrees.models import Degree


def process_student_import_logic(batch_id, file_path):
    batch = ImportBatch.objects.get(id=batch_id)

    try:
        df = pd.read_excel(file_path, dtype=str).dropna(how='all')
        column_mapping = {
            'Mã SV': 'student_code',
            'Họ và Tên': 'full_name',
            'Ngày Sinh': 'date_of_birth',
            'Mã Khoa': 'faculty_code',
            'Mã Ngành': 'major_code',
            'Năm Nhập Học': 'enrollment_year',
            'Xếp Loại': 'classification',
            'Email': 'email',
            'email': 'email',
        }
        df.rename(columns=column_mapping, inplace=True)
    except Exception as e:
        batch.errors += 1
        batch.save()
        return False, f"Không thể đọc file: {str(e)}"

    inserted_count = 0
    updated_count = 0
    error_count = 0

    majors_dict = {m.code: m for m in Major.objects.select_related('faculty').all()}
    existing_students = {s.student_code: s for s in Student.objects.select_related('major').all()}

    items_to_create = []
    students_to_create = []
    students_to_update = []

    for index, row in df.iterrows():
        row_num = index + 2
        student_code = str(row.get('student_code', '')).strip()
        full_name = str(row.get('full_name', '')).strip()
        major_code = str(row.get('major_code', '')).strip()

        if not student_code or student_code == 'nan':
            items_to_create.append(ImportBatchItem(import_batch=batch, row_number=row_num, action='ERROR', error_message="Thiếu Mã SV"))
            error_count += 1
            continue

        if major_code not in majors_dict:
            items_to_create.append(ImportBatchItem(import_batch=batch, row_number=row_num, action='ERROR', error_message=f"Mã ngành '{major_code}' không hợp lệ"))
            error_count += 1
            continue

        major_obj = majors_dict[major_code]
        student_exists = existing_students.get(student_code)
        new_data = {'full_name': full_name, 'major_code': major_code}

        if student_exists:
            old_data = {
                'full_name': student_exists.full_name,
                'major_code': student_exists.major.code if student_exists.major else None
            }
            items_to_create.append(ImportBatchItem(
                import_batch=batch,
                row_number=row_num,
                student_code=student_code,
                action='UPDATE',
                old_value=old_data,
                new_value=new_data
            ))

            student_exists.full_name = full_name
            student_exists.major = major_obj
            if hasattr(major_obj, 'faculty'):
                student_exists.faculty = major_obj.faculty
            students_to_update.append(student_exists)
            updated_count += 1
        else:
            items_to_create.append(ImportBatchItem(
                import_batch=batch,
                row_number=row_num,
                student_code=student_code,
                action='INSERT',
                new_value=new_data
            ))

            email_val = str(row.get('email', '')).strip()
            if not email_val or email_val == 'nan':
                email_val = f"{student_code.lower()}@student.ctuet.edu.vn"

            new_student = Student(
                student_code=student_code,
                full_name=full_name,
                major=major_obj,
                email=email_val,
            )
            if hasattr(major_obj, 'faculty'):
                new_student.faculty = major_obj.faculty

            enrollment_year = str(row.get('enrollment_year', '')).strip()
            if enrollment_year.isdigit():
                new_student.enrollment_year = int(enrollment_year)

            students_to_create.append(new_student)
            existing_students[student_code] = new_student
            inserted_count += 1

    with transaction.atomic():
        ImportBatchItem.objects.bulk_create(items_to_create)
        if students_to_create:
            Student.objects.bulk_create(students_to_create)
        if students_to_update:
            Student.objects.bulk_update(students_to_update, ['full_name', 'major', 'faculty'])

        batch.inserted = inserted_count
        batch.updated = updated_count
        batch.errors = error_count
        batch.status = 'completed'
        batch.save()

    return True, "Import thành công! Đã ghi dữ liệu vào bảng Sinh Viên."


def rollback_import_batch(batch_id):
    """Hoàn tác một đợt Import nếu sinh viên trong đợt chưa được cấp bằng"""
    batch = ImportBatch.objects.get(id=batch_id)
    if batch.status == 'rolled_back':
        raise ValidationError("Đợt import này đã được hoàn tác trước đó.")

    items = ImportBatchItem.objects.filter(import_batch=batch)
    affected_codes = [item.student_code for item in items if item.student_code]

    # Chặn hoàn tác nếu sinh viên đã có hồ sơ văn bằng được duyệt hoặc phát hành
    if Degree.objects.filter(student__student_code__in=affected_codes).exclude(status='DRAFT').exists():
        raise ValidationError("Không thể hoàn tác vì có sinh viên trong đợt này đã bước vào quy trình duyệt/cấp văn bằng.")

    with transaction.atomic():
        # 1. Xóa các sinh viên được INSERT mới trong đợt này
        insert_codes = [item.student_code for item in items if item.action == 'INSERT']
        if insert_codes:
            Student.objects.filter(student_code__in=insert_codes).delete()

        # 2. Khôi phục dữ liệu cũ cho các sinh viên bị UPDATE
        majors_dict = {m.code: m for m in Major.objects.select_related('faculty').all()}
        for item in items.filter(action='UPDATE'):
            if item.old_value and item.student_code:
                student = Student.objects.filter(student_code=item.student_code).first()
                if student:
                    student.full_name = item.old_value.get('full_name', student.full_name)
                    old_major_code = item.old_value.get('major_code')
                    if old_major_code and old_major_code in majors_dict:
                        student.major = majors_dict[old_major_code]
                        student.faculty = majors_dict[old_major_code].faculty
                    student.save()

        batch.status = 'rolled_back'
        batch.save()

    return True