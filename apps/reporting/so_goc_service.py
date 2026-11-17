"""
Dịch vụ xuất Sổ gốc cấp phát văn bằng, chứng chỉ chuẩn theo quy định
tại Thông tư số 21/2019/TT-BGDĐT của Bộ Giáo dục và Đào tạo.
Hỗ trợ kết xuất cả 2 định dạng: Excel (.xlsx) và PDF (.pdf).
"""
import io
from datetime import datetime
from django.utils import timezone
from django.template.loader import render_to_string
from django.conf import settings
from xhtml2pdf import pisa
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from apps.degrees.models import Degree
from apps.graduation.models import GraduationBatch


def get_so_goc_queryset(batch=None, degrees=None, batch_id=None):
    """Lấy danh sách văn bằng phục vụ lập Sổ gốc."""
    if degrees is not None and len(degrees) > 0:
        return degrees
    if batch_id:
        batch = GraduationBatch.objects.filter(id=batch_id).first()
    if batch:
        return Degree.objects.filter(batch=batch).select_related(
            'student', 'student__major', 'student__faculty', 'degree_type', 'batch'
        ).order_by('student__student_code')
    return Degree.objects.all().select_related(
        'student', 'student__major', 'student__faculty', 'degree_type', 'batch'
    ).order_by('-id')[:200]


def generate_so_goc_excel(batch=None, degrees=None, batch_id=None):
    """
    Tạo file Excel (.xlsx) 'Sổ gốc cấp phát văn bằng' chuẩn Thông tư 21/2019/TT-BGDĐT.
    """
    queryset = get_so_goc_queryset(batch=batch, degrees=degrees, batch_id=batch_id)
    if not batch and queryset.exists():
        batch = queryset.first().batch

    batch_name = batch.name if batch else "Toàn bộ hệ thống"
    decision_no = getattr(batch, 'decision_no', None) or "128/QĐ-ĐHKTCN"
    decision_date = getattr(batch, 'decision_date', None)
    decision_date_str = decision_date.strftime('%d/%m/%Y') if decision_date else timezone.now().strftime('%d/%m/%Y')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "So_Goc_Cap_Bang"

    # Định dạng trang in khổ ngang A4
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    ws.page_setup.paperSize = ws.PAPERSIZE_A4

    # Định dạng Font & Style
    font_bold_10 = Font(name="Times New Roman", size=10, bold=True)
    font_bold_11 = Font(name="Times New Roman", size=11, bold=True)
    font_regular_10 = Font(name="Times New Roman", size=10)
    font_italic_10 = Font(name="Times New Roman", size=10, italic=True)
    font_title = Font(name="Times New Roman", size=15, bold=True, color="1F4E78")
    font_header_table = Font(name="Times New Roman", size=10, bold=True, color="FFFFFF")

    fill_header = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    fill_sub_header = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")

    thin_border = Border(
        left=Side(style='thin', color='B0B0B0'),
        right=Side(style='thin', color='B0B0B0'),
        top=Side(style='thin', color='B0B0B0'),
        bottom=Side(style='thin', color='B0B0B0')
    )

    # 1. PHẦN QUỐC HIỆU VÀ CƠ QUAN CHỦ QUẢN
    ws.merge_cells("A1:F1")
    ws["A1"] = "BỘ GIÁO DỤC VÀ ĐÀO TẠO"
    ws["A1"].font = font_regular_10
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("A2:F2")
    ws["A2"] = "TRƯỜNG ĐẠI HỌC KỸ THUẬT - CÔNG NGHỆ CẦN THƠ"
    ws["A2"].font = font_bold_10
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("I1:P1")
    ws["I1"] = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM"
    ws["I1"].font = font_bold_10
    ws["I1"].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("I2:P2")
    ws["I2"] = "Độc lập - Tự do - Hạnh phúc"
    ws["I2"].font = font_bold_10
    ws["I2"].alignment = Alignment(horizontal="center", vertical="center")

    # 2. TIÊU ĐỀ SỔ GỐC
    ws.merge_cells("A4:P4")
    ws["A4"] = "SỔ GỐC CẤP PHÁT VĂN BẰNG, CHỨNG CHỈ"
    ws["A4"].font = font_title
    ws["A4"].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("A5:P5")
    ws["A5"] = "(Ban hành theo Thông tư số 21/2019/TT-BGDĐT ngày 29/11/2019 của Bộ trưởng Bộ GD&ĐT)"
    ws["A5"].font = font_italic_10
    ws["A5"].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("A6:P6")
    ws["A6"] = f"Đợt tốt nghiệp: {batch_name.upper()}  |  Theo Quyết định số: {decision_no} ký ngày {decision_date_str}"
    ws["A6"].font = font_bold_11
    ws["A6"].alignment = Alignment(horizontal="center", vertical="center")

    # 3. TIÊU ĐỀ CÁC CỘT (THEO THÔNG TƯ 21/2019)
    headers = [
        "STT",
        "Số vào sổ gốc",
        "Số hiệu văn bằng",
        "Họ và tên",
        "Mã SV",
        "Ngày sinh",
        "Giới tính",
        "Nơi sinh",
        "Ngành đào tạo",
        "Xếp loại tốt nghiệp",
        "Điểm GPA",
        "Năm tốt nghiệp",
        "Mã băm On-Chain (Hash)",
        "Trạng thái Blockchain",
        "Chữ ký người nhận",
        "Ghi chú (IPFS CID)"
    ]

    row_header = 8
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=row_header, column=col_idx, value=h)
        cell.font = font_header_table
        cell.fill = fill_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border
    ws.row_dimensions[row_header].height = 28

    # 4. ĐỔ DỮ LIỆU CÁC DÒNG
    current_row = row_header + 1
    for idx, d in enumerate(queryset, 1):
        sv = d.student
        dob_str = sv.date_of_birth.strftime('%d/%m/%Y') if sv and sv.date_of_birth else "-"
        gender_str = sv.get_gender_display() if sv and hasattr(sv, 'get_gender_display') else "Nam"
        pob_str = sv.current_address if sv and sv.current_address else "Cần Thơ"
        major_str = sv.major.name if sv and sv.major else (d.degree_type.name if d.degree_type else "N/A")
        gpa_str = f"{sv.gpa_score:.2f}" if sv and sv.gpa_score is not None else "-"
        grad_year = str(d.graduation_year or (batch.decision_date.year if batch and batch.decision_date else 2026))

        so_vao_so = f"{idx:03d}/{grad_year}/SGCB-CTUT"
        so_hieu = d.serial_number
        hash_short = f"{d.canonical_hash[:8]}...{d.canonical_hash[-6:]}" if d.canonical_hash else "-"
        ipfs_short = f"{d.ipfs_cid[:6]}...{d.ipfs_cid[-4:]}" if d.ipfs_cid else "-"
        chain_status = "Đã xác thực On-Chain" if d.status == 'ISSUED' else d.get_status_display()
        receiver_sign = "Đã nhận bằng điện tử" if d.status == 'ISSUED' else "Chưa nhận"

        row_data = [
            idx,
            so_vao_so,
            so_hieu,
            sv.full_name if sv else "N/A",
            sv.student_code if sv else "N/A",
            dob_str,
            gender_str,
            pob_str,
            major_str,
            d.classification or "Khá",
            gpa_str,
            grad_year,
            hash_short,
            chain_status,
            receiver_sign,
            ipfs_short
        ]

        for col_idx, val in enumerate(row_data, 1):
            cell = ws.cell(row=current_row, column=col_idx, value=val)
            cell.font = font_regular_10
            cell.border = thin_border
            # Căn giữa cho các cột ngắn
            if col_idx in [1, 2, 3, 5, 6, 7, 10, 11, 12, 13, 14, 15, 16]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

        ws.row_dimensions[current_row].height = 20
        current_row += 1

    # 5. PHẦN CHỮ KÝ VÀ NGÀY THÁNG CUỐI SỔ
    current_row += 1
    today = timezone.now()
    date_str = f"Cần Thơ, ngày {today.day:02d} tháng {today.month:02d} năm {today.year}"

    ws.merge_cells(start_row=current_row, start_column=11, end_row=current_row, end_column=16)
    cell_date = ws.cell(row=current_row, column=11, value=date_str)
    cell_date.font = font_italic_10
    cell_date.alignment = Alignment(horizontal="center", vertical="center")

    current_row += 1
    # 3 Khối ký tên
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=4)
    ws.cell(row=current_row, column=1, value="NGƯỜI LẬP SỔ").font = font_bold_10
    ws.cell(row=current_row, column=1).alignment = Alignment(horizontal="center")

    ws.merge_cells(start_row=current_row, start_column=6, end_row=current_row, end_column=9)
    ws.cell(row=current_row, column=6, value="TRƯỞNG PHÒNG ĐÀO TẠO").font = font_bold_10
    ws.cell(row=current_row, column=6).alignment = Alignment(horizontal="center")

    ws.merge_cells(start_row=current_row, start_column=12, end_row=current_row, end_column=16)
    ws.cell(row=current_row, column=12, value="HIỆU TRƯỞNG").font = font_bold_10
    ws.cell(row=current_row, column=12).alignment = Alignment(horizontal="center")

    current_row += 1
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=4)
    ws.cell(row=current_row, column=1, value="(Ký, ghi rõ họ tên)").font = font_italic_10
    ws.cell(row=current_row, column=1).alignment = Alignment(horizontal="center")

    ws.merge_cells(start_row=current_row, start_column=6, end_row=current_row, end_column=9)
    ws.cell(row=current_row, column=6, value="(Ký, ghi rõ họ tên)").font = font_italic_10
    ws.cell(row=current_row, column=6).alignment = Alignment(horizontal="center")

    ws.merge_cells(start_row=current_row, start_column=12, end_row=current_row, end_column=16)
    ws.cell(row=current_row, column=12, value="(Ký tên và đóng dấu)").font = font_italic_10
    ws.cell(row=current_row, column=12).alignment = Alignment(horizontal="center")

    # Tự động canh chỉnh độ rộng cột
    col_widths = {
        'A': 6,   # STT
        'B': 20,  # Số vào sổ
        'C': 18,  # Số hiệu văn bằng
        'D': 24,  # Họ và tên
        'E': 12,  # Mã SV
        'F': 13,  # Ngày sinh
        'G': 10,  # Giới tính
        'H': 14,  # Nơi sinh
        'I': 26,  # Ngành đào tạo
        'J': 16,  # Xếp loại
        'K': 10,  # GPA
        'L': 12,  # Năm tốt nghiệp
        'M': 20,  # Hash
        'N': 18,  # Blockchain Status
        'O': 20,  # Chữ ký người nhận
        'P': 16,  # IPFS
    }
    for col_letter, w in col_widths.items():
        ws.column_dimensions[col_letter].width = w

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


def generate_so_goc_pdf(batch=None, degrees=None, batch_id=None):
    """
    Tạo file PDF 'Sổ gốc cấp phát văn bằng' chuẩn Thông tư 21/2019/TT-BGDĐT.
    """
    queryset = get_so_goc_queryset(batch=batch, degrees=degrees, batch_id=batch_id)
    if not batch and queryset.exists():
        batch = queryset.first().batch

    batch_name = batch.name if batch else "Toàn bộ hệ thống"
    decision_no = getattr(batch, 'decision_no', None) or "128/QĐ-ĐHKTCN"
    decision_date = getattr(batch, 'decision_date', None)
    decision_date_str = decision_date.strftime('%d/%m/%Y') if decision_date else timezone.now().strftime('%d/%m/%Y')

    rows = []
    for idx, d in enumerate(queryset, 1):
        sv = d.student
        grad_year = str(d.graduation_year or (batch.decision_date.year if batch and batch.decision_date else 2026))
        rows.append({
            'stt': idx,
            'so_vao_so': f"{idx:03d}/{grad_year}/SGCB-CTUT",
            'so_hieu': d.serial_number,
            'ho_ten': sv.full_name if sv else "N/A",
            'mssv': sv.student_code if sv else "N/A",
            'ngay_sinh': sv.date_of_birth.strftime('%d/%m/%Y') if sv and sv.date_of_birth else "-",
            'gioi_tinh': sv.get_gender_display() if sv and hasattr(sv, 'get_gender_display') else "Nam",
            'noi_sinh': sv.current_address if sv and sv.current_address else "Cần Thơ",
            'nganh': sv.major.name if sv and sv.major else (d.degree_type.name if d.degree_type else "N/A"),
            'xep_loai': d.classification or "Khá",
            'gpa': f"{sv.gpa_score:.2f}" if sv and sv.gpa_score is not None else "-",
            'nam_tn': grad_year,
            'hash_short': f"{d.canonical_hash[:8]}...{d.canonical_hash[-6:]}" if d.canonical_hash else "-",
            'chain_status': "On-Chain" if d.status == 'ISSUED' else d.get_status_display(),
            'receiver_sign': "Đã cấp điện tử" if d.status == 'ISSUED' else "Chưa nhận",
            'ipfs_short': f"{d.ipfs_cid[:6]}...{d.ipfs_cid[-4:]}" if d.ipfs_cid else "-",
        })

    today = timezone.now()
    context = {
        'batch_name': batch_name,
        'decision_no': decision_no,
        'decision_date_str': decision_date_str,
        'rows': rows,
        'today_str': f"Cần Thơ, ngày {today.day:02d} tháng {today.month:02d} năm {today.year}",
    }

    html_content = render_to_string('reporting/so_goc_pdf.html', context)
    pdf_buffer = io.BytesIO()

    from apps.degrees.pdf_generator import link_callback
    pisa_status = pisa.CreatePDF(
        src=html_content,
        dest=pdf_buffer,
        encoding='utf-8',
        link_callback=link_callback
    )
    if pisa_status.err:
        return None
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()
