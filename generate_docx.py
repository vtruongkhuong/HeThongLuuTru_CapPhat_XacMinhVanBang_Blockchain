import os
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, hex_color):
    tcPr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=120, bottom=120, left=180, right=180):
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def set_table_borders(table, color="CCCCCC", sz="4", val="single"):
    tblPr = table._element.xpath('w:tblPr')
    if tblPr:
        borders = parse_xml(
            f'<w:tblBorders {nsdecls("w")}>'
            f'<w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:insideV w:val="none"/>'
            f'<w:left w:val="none"/>'
            f'<w:right w:val="none"/>'
            f'</w:tblBorders>'
        )
        tblPr[0].append(borders)

def add_callout(doc, text_content, title="LƯU Ý QUAN TRỌNG"):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    cell = tbl.cell(0, 0)
    cell.width = Inches(6.5)
    set_cell_background(cell, "F0F4F8")
    set_cell_margins(cell, top=140, bottom=140, left=200, right=200)
    
    tcPr = cell._element.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:left w:val="single" w:sz="24" w:space="0" w:color="0066CC"/>'
        f'<w:top w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'<w:bottom w:val="none"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(4)
    run_t = p.add_run(f"📌 {title}: ")
    run_t.bold = True
    run_t.font.name = "Arial"
    run_t.font.size = Pt(10)
    run_t.font.color.rgb = RGBColor(0, 102, 204)
    
    run_c = p.add_run(text_content)
    run_c.font.name = "Arial"
    run_c.font.size = Pt(10)
    run_c.font.color.rgb = RGBColor(51, 51, 51)
    
    p_after = doc.add_paragraph()
    p_after.paragraph_format.space_before = Pt(0)
    p_after.paragraph_format.space_after = Pt(4)

def add_code_block(doc, code_str):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    cell.width = Inches(6.5)
    set_cell_background(cell, "F8F9FA")
    set_cell_margins(cell, top=100, bottom=100, left=150, right=150)
    
    tcPr = cell._element.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:left w:val="single" w:sz="6" w:space="0" w:color="D0D5DD"/>'
        f'<w:top w:val="single" w:sz="6" w:space="0" w:color="D0D5DD"/>'
        f'<w:right w:val="single" w:sz="6" w:space="0" w:color="D0D5DD"/>'
        f'<w:bottom w:val="single" w:sz="6" w:space="0" w:color="D0D5DD"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.15
    run = p.add_run(code_str)
    run.font.name = "Consolas"
    run.font.size = Pt(8.5)
    run.font.color.rgb = RGBColor(33, 37, 41)
    
    p_after = doc.add_paragraph()
    p_after.paragraph_format.space_before = Pt(0)
    p_after.paragraph_format.space_after = Pt(4)

def main():
    doc = Document()
    
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)
        
        footer = section.footer
        p_ft = footer.paragraphs[0]
        p_ft.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r_ft = p_ft.add_run("Hệ thống Quản lý, Cấp phát và Xác minh Văn bằng trên Blockchain")
        r_ft.font.name = "Arial"
        r_ft.font.size = Pt(8.5)
        r_ft.font.color.rgb = RGBColor(128, 128, 128)

    # Tiêu đề chính
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(4)
    run_title = p_title.add_run("KIẾN TRÚC LƯU TRỮ VÀ GIAO DỊCH BLOCKCHAIN")
    run_title.font.name = "Arial"
    run_title.font.size = Pt(20)
    run_title.bold = True
    run_title.font.color.rgb = RGBColor(27, 54, 93)

    # Tiêu đề phụ
    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(18)
    run_sub = p_sub.add_run("Bảo Vệ Điểm Số Bằng Mật Mã Học, Cấp Phát Đơn Lẻ, Đối Soát & Thống Kê Transaction")
    run_sub.font.name = "Arial"
    run_sub.font.size = Pt(11)
    run_sub.italic = True
    run_sub.font.color.rgb = RGBColor(80, 90, 105)

    p_meta = doc.add_paragraph()
    p_meta.paragraph_format.space_after = Pt(14)
    r_meta = p_meta.add_run("Dự án: Hệ thống Quản lý, Cấp phát và Xác minh Văn bằng trên Blockchain\nSmart Contract: DegreeVerification.sol (Mạng Ethereum Sepolia Testnet)\nBackend & Framework: Django, PostgreSQL, Celery, Redis, Web3.py")
    r_meta.font.name = "Arial"
    r_meta.font.size = Pt(9.5)
    r_meta.font.color.rgb = RGBColor(100, 100, 100)

    def add_h1(text):
        h = doc.add_paragraph()
        h.paragraph_format.space_before = Pt(14)
        h.paragraph_format.space_after = Pt(6)
        h.paragraph_format.keep_with_next = True
        run = h.add_run(text)
        run.font.name = "Arial"
        run.font.size = Pt(14)
        run.bold = True
        run.font.color.rgb = RGBColor(27, 54, 93)
        return h

    def add_h2(text):
        h = doc.add_paragraph()
        h.paragraph_format.space_before = Pt(10)
        h.paragraph_format.space_after = Pt(4)
        h.paragraph_format.keep_with_next = True
        run = h.add_run(text)
        run.font.name = "Arial"
        run.font.size = Pt(12)
        run.bold = True
        run.font.color.rgb = RGBColor(0, 102, 204)
        return h

    def add_p(text, bold_prefix=None, italic=False):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(5)
        p.paragraph_format.line_spacing = 1.2
        if bold_prefix:
            rb = p.add_run(bold_prefix)
            rb.font.name = "Arial"
            rb.font.size = Pt(10)
            rb.bold = True
            rb.font.color.rgb = RGBColor(33, 37, 41)
        r = p.add_run(text)
        r.font.name = "Arial"
        r.font.size = Pt(10)
        r.italic = italic
        r.font.color.rgb = RGBColor(51, 51, 51)
        return p

    def add_bullet(text, bold_prefix=None):
        p = doc.add_paragraph(style='List Bullet')
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            rb = p.add_run(bold_prefix)
            rb.font.name = "Arial"
            rb.font.size = Pt(10)
            rb.bold = True
            rb.font.color.rgb = RGBColor(33, 37, 41)
        r = p.add_run(text)
        r.font.name = "Arial"
        r.font.size = Pt(10)
        r.font.color.rgb = RGBColor(51, 51, 51)
        return p

    # 1. KIẾN TRÚC LƯU TRỮ
    add_h1("1. KIẾN TRÚC LƯU TRỮ ON-CHAIN VÀ OFF-CHAIN")
    add_p("Hệ thống áp dụng mô hình kiến trúc lưu trữ lai (Hybrid Storage Architecture), kết hợp tối ưu giữa Cơ sở dữ liệu quan hệ truyền thống và Chuỗi khối (Blockchain Ethereum Sepolia).")
    
    table_data = [
        ("Tiêu chí", "Lưu trữ Off-chain (Django & CSDL)", "Lưu trữ On-chain (Ethereum Sepolia)"),
        ("Nơi lưu trữ vật lý", "Cơ sở dữ liệu PostgreSQL (Neon.tech Cloud) và ổ đĩa media máy chủ (media/degrees/).", "Hợp đồng thông minh DegreeVerification.sol trên Ethereum Sepolia Testnet."),
        ("Dữ liệu định danh cá nhân (PII)", "Họ tên, ngày sinh, CCCD/CMND, email, số điện thoại, GPA, ảnh chân dung sinh viên.", "HOÀN TOÀN KHÔNG LƯU DẠNG RÕ. Chỉ lưu mã băm mật mã học một chiều (Keccak-256) khóa cứng toàn vẹn dữ liệu."),
        ("Dữ liệu văn bằng & học vụ", "Khoa, ngành, loại bằng, số hiệu, xếp loại, ngày cấp, file PDF gốc đã kết xuất.", "Lưu mã Merkle Root (bytes32) gom cho đợt tốt nghiệp hoặc mã băm lá trực tiếp cho văn bằng đơn lẻ."),
        ("Xử lý sai sót & Thu hồi", "Lưu phiếu yêu cầu thu hồi, lý do dạng văn bản chi tiết, người đề xuất, người duyệt, văn bằng thay thế (supersedes).", "Đánh dấu mã băm lá (leaf) là đã thu hồi kèm mã lý do số (uint8 reason), thời gian thu hồi (uint64)."),
        ("Quy trình 4 mắt & Phân quyền", "Maker, Checker, Approver, lịch sử import và rollback (old_value / new_value).", "Quyền hạn của các địa chỉ ví ký phát hành (Owner, Admin đồng cấp, Issuer)."),
        ("Chi phí lưu trữ", "Chi phí cơ sở dữ liệu quan hệ thông thường.", "Cực kỳ tối ưu gas: 1 đợt hàng nghìn sinh viên chỉ tốn 1 slot lưu trữ Merkle Root 32 bytes.")
    ]

    tbl1 = doc.add_table(rows=len(table_data), cols=3)
    tbl1.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl1.autofit = False
    set_table_borders(tbl1, color="B0C4DE")

    col_widths = [Inches(1.5), Inches(2.5), Inches(2.5)]

    for row_idx, row in enumerate(tbl1.rows):
        is_header = (row_idx == 0)
        for col_idx, cell in enumerate(row.cells):
            cell.width = col_widths[col_idx]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            set_cell_margins(cell, top=100, bottom=100, left=140, right=140)
            
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.15
            
            text = table_data[row_idx][col_idx]
            run = p.add_run(text)
            run.font.name = "Arial"
            
            if is_header:
                set_cell_background(cell, "1B365D")
                run.bold = True
                run.font.size = Pt(9.5)
                run.font.color.rgb = RGBColor(255, 255, 255)
            else:
                bg = "F9FAFC" if (row_idx % 2 == 1) else "FFFFFF"
                set_cell_background(cell, bg)
                run.font.size = Pt(9.0)
                if col_idx == 0:
                    run.bold = True
                    run.font.color.rgb = RGBColor(27, 54, 93)
                else:
                    run.font.color.rgb = RGBColor(51, 51, 51)

    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_before = Pt(4)
    p_sp.paragraph_format.space_after = Pt(4)

    # 2. CƠ CHẾ BẢO VỆ ĐIỂM SỐ
    add_h1("2. CƠ CHẾ BẢO VỆ ĐIỂM SỐ BẰNG MẬT MÃ HỌC (CHỐNG SỬA ĐIỂM)")
    add_p("Một hiểu lầm phổ biến là: 'Nếu không lưu chữ điểm 3.8 lên Blockchain thì quản trị viên CSDL vào sửa điểm thì sao?'. Hệ thống giải quyết triệt để vấn đề này bằng nguyên lý Khóa Cứng Mật Mã Học (Cryptographic Integrity Locking):")
    
    add_bullet(" Toàn bộ các trường dữ liệu cốt lõi bao gồm: student_code, full_name, major_code, degree_type_code, batch_name, classification và ĐIỂM GPA (gpa_score) được đưa vào đối tượng JSON chuẩn hóa và băm bằng giải thuật Keccak-256.", bold_prefix="1. Băm chuẩn hóa bao gồm Điểm GPA: ")
    add_bullet(" Nhờ hiệu ứng tuyết lở (Avalanche Effect) của hàm băm Keccak-256: Chỉ cần kẻ xấu vào PostgreSQL sửa điểm GPA từ 2.85 lên 3.85, toàn bộ chuỗi 64 ký tự của Canonical Hash sẽ biến đổi hoàn toàn.", bold_prefix="2. Hiệu ứng Tuyết Lở (Avalanche Effect): ")
    add_bullet(" Khi nhà tuyển dụng quét QR xác minh hoặc khi lệnh đối soát reconcile_chain chạy nửa đêm, hệ thống lấy dữ liệu hiện tại trong DB băm lại. Do điểm bị sửa, mã băm mới không thể khớp với Merkle Proof và Merkle Root đã chốt cứng trên Smart Contract -> Hệ thống lập tức BÁO ĐỘNG GIAN LẬN và từ chối xác thực văn bằng.", bold_prefix="3. Phát hiện Gian lận tức thì: ")

    add_callout(doc, "Blockchain không cần lưu trữ chữ '3.85' dạng bản rõ (plaintext). Bằng việc lưu trữ dấu vân tay mật mã (Merkle Root) của toàn bộ dữ liệu bao gồm điểm GPA, Blockchain bảo vệ điểm số an toàn tuyệt đối 100% trước mọi hành vi sửa lén trong cơ sở dữ liệu.", title="KẾT LUẬN VỀ BẢO VỆ ĐIỂM SỐ")

    # 3. QUY TRÌNH PHÁT HÀNH VĂN BẰNG ĐƠN LẺ
    add_h1("3. TÍNH NĂNG PHÁT HÀNH VĂN BẰNG ĐƠN LẺ (SINGLE DEGREE ISSUANCE)")
    add_p("Bên cạnh cơ chế cấp phát theo lô (Batch Issuance), hệ thống đã hoàn thiện tính năng Phát hành văn bằng đơn lẻ dành cho các trường hợp sinh viên tốt nghiệp đợt phụ, cấp lại văn bằng bị mất, hoặc cấp chứng chỉ ngắn hạn riêng lẻ:")

    add_bullet(" Cán bộ giáo vụ chọn 1 văn bằng ở trạng thái DRAFT / GENERATED và bấm action '1. [Đơn lẻ] Trình duyệt văn bằng'. Hệ thống kiểm tra hợp lệ và chuyển trạng thái sang REVIEWED.", bold_prefix="Bước 1 - Trình duyệt (Maker - officer_a): ")
    add_bullet(" Cán bộ phê duyệt chọn văn bằng và bấm action '2. [Đơn lẻ] Phê duyệt & Cấp phôi On-Chain'. Hệ thống kiểm tra quy tắc 4-mắt (Maker ≠ Checker), tự động sinh Canonical Hash (bao gồm điểm GPA), tạo IssuanceBatch đơn lẻ (với count=1, Merkle Root = Leaf Hash), tạo Merkle Proof (proof_path = []) và kết xuất file PDF ngay lập tức.", bold_prefix="Bước 2 - Phê duyệt (Checker - officer_b): ")
    add_bullet(" Cán bộ phát hành chọn văn bằng APPROVED và bấm action '3. [Đơn lẻ] Ký phát hành qua MetaMask'. Giao diện Web3 hiển thị thông tin sinh viên, điểm số và mã hash lá, sau đó gọi hàm storeMerkleRoot(batchName, leaf_hash, 1) trên mạng Sepolia. Khi giao dịch được xác nhận, văn bằng chính thức chuyển sang trạng thái ISSUED.", bold_prefix="Bước 3 - Ký phát hành Web3 (Issuer): ")

    # 4. TRUY VẾT & ĐỐI SOÁT
    add_h1("4. CƠ CHẾ TRUY VẾT LỊCH SỬ VÀ ĐỐI SOÁT DỮ LIỆU")
    add_p("Hệ thống thiết lập 4 tầng truy vết độc lập:")
    add_bullet(" Bảng AuditLog ghi vết mọi sự kiện (LOGIN, IMPORT_EXCEL, ROLLBACK, RENDER_PDF, APPROVE_BATCH, ISSUE_DEGREE, REVOKE_DEGREE) kèm IP, User-Agent, và snapshot JSON old_value/new_value.", bold_prefix="1. Nhật ký Kiểm toán (AuditLog): ")
    add_bullet(" Bắt buộc 3 bước trong quy trình cấp phát (Maker, Checker, Issuer) phải do 3 tài khoản người dùng khác nhau thực hiện thông qua hàm ensure_different_actors().", bold_prefix="2. Quy tắc 4 mắt (Four-eyes Principle): ")
    add_bullet(" Cho phép Hoàn tác toàn bộ file Excel hoặc Hoàn tác đơn lẻ từng dòng sinh viên bị sai lệch về lại trạng thái cũ.", bold_prefix="3. Lịch sử Import & Hoàn tác: ")
    add_bullet(" Celery Beat chạy lệnh reconcile_chain tự động vào mỗi nửa đêm: kiểm tra giao dịch pending, đối soát toàn vẹn Merkle Root giữa DB và Smart Contract, và đối soát trạng thái văn bằng bị thu hồi.", bold_prefix="4. Đối soát định kỳ (reconcile_chain): ")

    # 5. THỐNG KÊ TRANSACTION
    add_h1("5. PHÂN LOẠI VÀ THỐNG KÊ CÁC TRANSACTION TRONG HỆ THỐNG")
    add_p("Hệ thống có tổng cộng 9 loại Transaction (giao dịch có ký số, làm thay đổi trạng thái và tốn gas) chia thành 3 nhóm:")
    add_bullet(" Triển khai hợp đồng DegreeVerification.sol lên mạng Sepolia, gán quyền Owner, Admin và Issuer ban đầu.", bold_prefix="Tx 1 - Deploy Contract: ")
    add_bullet(" Ký qua ví MetaMask gọi storeMerkleRoot ghi nhận Merkle Root của đợt tốt nghiệp hoặc của văn bằng đơn lẻ (count=1).", bold_prefix="Tx 2 - storeMerkleRoot (Ký phát hành đợt / đơn lẻ): ")
    add_bullet(" Ký qua ví MetaMask gọi revokeDegree ghi nhận mã băm lá bị thu hồi kèm mã số lý do lên chuỗi.", bold_prefix="Tx 3 - revokeDegree (Ký thu hồi văn bằng): ")
    add_bullet(" Cấp quyền Quản trị viên đồng cấp có đầy đủ quyền hạn như Owner.", bold_prefix="Tx 4 - addAdmin: ")
    add_bullet(" Hủy quyền Quản trị viên của một địa chỉ ví.", bold_prefix="Tx 5 - removeAdmin: ")
    add_bullet(" Cấp quyền ký phát hành và thu hồi cho một ví Cán bộ đào tạo mới.", bold_prefix="Tx 6 - addIssuer: ")
    add_bullet(" Gỡ quyền ký phát hành khi cán bộ luân chuyển công tác.", bold_prefix="Tx 7 - removeIssuer: ")
    add_bullet(" Khóa hoặc mở khóa khẩn cấp quyền ký của một ví cán bộ khi nghi vấn lộ Private Key.", bold_prefix="Tx 8 - pauseIssuer / unpauseIssuer: ")
    add_bullet(" Chuyển giao quyền sở hữu hợp đồng tối cao an toàn theo quy trình 2 bước.", bold_prefix="Tx 9 - transferOwnership & acceptOwnership: ")

    # 6. LỘ TRÌNH MỞ RỘNG
    add_h1("6. ĐỊNH HƯỚNG MỞ RỘNG HỆ THỐNG (ROADMAP NÂNG CẤP WEB3)")
    add_p("Để tiếp tục nâng tầm hệ thống thành một siêu ứng dụng (Super DApp) giáo dục toàn diện, các tính năng sau được định hướng phát triển:")
    add_bullet(" Đẩy file PDF văn bằng lên mạng lưu trữ ngang hàng toàn cầu IPFS (InterPlanetary File System), lưu mã IPFS CID lên Smart Contract, đảm bảo văn bằng tồn tại vĩnh viễn và phi tập trung 100%.", bold_prefix="1. Lưu trữ IPFS Phi Tập Trung: ")
    add_bullet(" Mint mỗi văn bằng thành một NFT không thể chuyển nhượng (Soulbound Token - ERC-5114 / ERC-721) trực tiếp vào ví MetaMask của sinh viên, cho phép sinh viên xem tấm bằng của mình trong tab NFT của ví cá nhân.", bold_prefix="2. Soulbound Token (SBT NFT): ")
    add_bullet(" Cho phép cán bộ và sinh viên đăng nhập hệ thống trực tiếp bằng nút 'Connect with MetaMask' theo chuẩn EIP-4361 bên cạnh đăng nhập email thông thường.", bold_prefix="3. Đăng nhập Ví Web3 (Sign-In with Ethereum - SIWE): ")
    add_bullet(" Cung cấp giao diện cho các phòng nhân sự (HR) kéo thả hàng loạt 50 file PDF ứng viên để hệ thống tự động kiểm tra chữ ký số và đối soát chuỗi trong 3 giây.", bold_prefix="4. Cổng Doanh nghiệp Xác minh Hàng loạt (Bulk Verification): ")

    # 7. PHỤ LỤC SMART CONTRACT
    add_h1("7. CẤU TRÚC CHI TIẾT SMART CONTRACT DEGREEVERIFICATION.SOL")
    add_p("Hợp đồng được viết bằng ngôn ngữ Solidity ^0.8.20 với các kỹ thuật tối ưu gas vượt trội: Custom Errors (tiết kiệm gas khi revert), Storage Slot Packing (gom struct Batch vừa khít 2 slots 32 bytes tiết kiệm 20.000 gas mỗi lần ghi), Modifiers kiểm soát quyền hạn 3 lớp, và hàm external view verifyDegree xác minh proof trực tiếp trên EVM miễn phí gas.")

    out_dir = r"d:\HeThongLuuTru_CapPhat_XacMinhVanBang_Blockchain-main"
    out_path = os.path.join(out_dir, "Kien_Truc_Luu_Tru_Va_Transaction_Blockchain.docx")
    doc.save(out_path)
    print(f"Successfully generated DOCX at: {out_path}")

if __name__ == "__main__":
    main()
