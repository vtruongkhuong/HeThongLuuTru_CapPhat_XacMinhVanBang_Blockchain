"""
Logic đọc file Excel/CSV sinh viên, validate từng dòng, dedup theo
student_code, và ghi kết quả vào ImportBatch.

Được gọi từ apps.students.tasks (Celery task chạy bất đồng bộ), tách riêng
ra module này để dễ unit test độc lập với Celery.
"""
import csv
import io
from dataclasses import dataclass, field
from datetime import datetime

import openpyxl
from django.db import transaction

from apps.academic.models import Faculty, Major
from .models import Student, ImportBatch

# Các cột bắt buộc trong file import, theo đúng thứ tự header mong đợi.
REQUIRED_COLUMNS = [
    'student_code', 'full_name', 'date_of_birth', 'gender',
    'national_id', 'email', 'phone_number',
    'faculty_code', 'major_code', 'enrollment_year',
]


@dataclass
class RowError:
    row: int
    error: str


@dataclass
class ImportResult:
    total_rows: int = 0
    success_rows: int = 0
    error_rows: int = 0
    errors: list = field(default_factory=list)


def _read_rows_from_csv(file_obj):
    content = file_obj.read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(content))
    return list(reader)


def _read_rows_from_excel(file_obj):
    wb = openpyxl.load_workbook(file_obj, data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    headers = [str(h).strip() for h in next(rows_iter)]
    rows = []
    for raw_row in rows_iter:
        if all(cell is None for cell in raw_row):
            continue  # bỏ qua dòng trống
        rows.append(dict(zip(headers, raw_row)))
    return rows


def _parse_date(value):
    if value is None or value == '':
        return None
    if isinstance(value, datetime):
        return value.date()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
        try:
            return datetime.strptime(str(value), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Không parse được ngày sinh: '{value}'")


def _validate_row(row: dict, row_number: int, seen_codes: set) -> dict:
    """
    Validate 1 dòng dữ liệu. Raise ValueError nếu lỗi, trả về dict đã
    chuẩn hóa (sẵn sàng tạo Student) nếu hợp lệ.
    """
    missing = [col for col in REQUIRED_COLUMNS if not str(row.get(col, '')).strip()]
    # enrollment_year và date_of_birth cho phép rỗng tùy nghiệp vụ, nên loại trừ ở đây nếu cần
    missing = [c for c in missing if c not in ('date_of_birth',)]
    if missing:
        raise ValueError(f"Thiếu cột bắt buộc: {', '.join(missing)}")

    student_code = str(row['student_code']).strip()

    # Dedup trong cùng file
    if student_code in seen_codes:
        raise ValueError(f"Mã sinh viên '{student_code}' bị trùng trong file import")
    seen_codes.add(student_code)

    # Dedup với dữ liệu đã có trong DB
    if Student.objects.filter(student_code=student_code).exists():
        raise ValueError(f"Mã sinh viên '{student_code}' đã tồn tại trong hệ thống")

    try:
        faculty = Faculty.objects.get(code=str(row['faculty_code']).strip())
    except Faculty.DoesNotExist:
        raise ValueError(f"Không tìm thấy Khoa với mã '{row['faculty_code']}'")

    try:
        major = Major.objects.get(code=str(row['major_code']).strip())
    except Major.DoesNotExist:
        raise ValueError(f"Không tìm thấy Ngành với mã '{row['major_code']}'")

    gender = str(row.get('gender', '')).strip().upper()[:1]
    if gender not in ('M', 'F', 'O', ''):
        raise ValueError(f"Giới tính không hợp lệ: '{row.get('gender')}'")

    try:
        enrollment_year = int(row['enrollment_year'])
    except (ValueError, TypeError):
        raise ValueError(f"Năm nhập học không hợp lệ: '{row.get('enrollment_year')}'")

    return {
        'student_code': student_code,
        'full_name': str(row['full_name']).strip(),
        'date_of_birth': _parse_date(row.get('date_of_birth')),
        'gender': gender,
        'national_id': str(row.get('national_id', '')).strip(),
        'email': str(row.get('email', '')).strip(),
        'phone_number': str(row.get('phone_number', '')).strip(),
        'faculty': faculty,
        'major': major,
        'enrollment_year': enrollment_year,
    }


def run_import(batch: ImportBatch) -> ImportResult:
    """
    Điểm vào chính: đọc file trong batch.source_file, validate từng dòng,
    tạo Student cho dòng hợp lệ. Dòng lỗi không làm dừng cả batch (best-effort),
    nhưng mỗi Student được tạo trong transaction riêng để đảm bảo idempotency
    (nếu task bị retry, dòng đã import thành công sẽ bị chặn bởi check dedup).
    """
    result = ImportResult()
    seen_codes = set()

    filename = batch.source_file.name.lower()
    batch.source_file.open('rb')
    try:
        if filename.endswith('.csv'):
            rows = _read_rows_from_csv(batch.source_file)
        else:
            rows = _read_rows_from_excel(batch.source_file)
    finally:
        batch.source_file.close()

    result.total_rows = len(rows)

    for idx, row in enumerate(rows, start=2):  # dòng 1 là header
        try:
            with transaction.atomic():
                cleaned = _validate_row(row, idx, seen_codes)
                Student.objects.create(**cleaned)
            result.success_rows += 1
        except ValueError as e:
            result.error_rows += 1
            result.errors.append({'row': idx, 'error': str(e)})
        except Exception as e:  # lỗi không lường trước, vẫn ghi nhận thay vì crash cả batch
            result.error_rows += 1
            result.errors.append({'row': idx, 'error': f"Lỗi không xác định: {e}"})

    return result
