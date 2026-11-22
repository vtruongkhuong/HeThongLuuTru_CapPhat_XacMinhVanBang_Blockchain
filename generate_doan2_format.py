import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

doc = docx.Document()

# Căn lề chuẩn như file Đồ án 2
for s in doc.sections:
    s.top_margin = Inches(0.79)
    s.bottom_margin = Inches(0.79)
    s.left_margin = Inches(1.18)
    s.right_margin = Inches(0.79)

def set_cell_background(cell, fill_hex):
    tcPr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def add_header(title, level, color=RGBColor(0, 51, 102)):
    p = doc.add_heading(level=level)
    run = p.add_run(title)
    run.font.name = 'Times New Roman'
    run.font.size = Pt(16 if level == 1 else (14 if level == 2 else 13))
    run.font.bold = True
    run.font.color.rgb = color
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.3
    return p

def add_para(text, bold_prefix="", italic=False):
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.3
    p.paragraph_format.space_after = Pt(4)
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.font.name = 'Times New Roman'
        r_pre.font.size = Pt(13)
        r_pre.font.bold = True
    r = p.add_run(text)
    r.font.name = 'Times New Roman'
    r.font.size = Pt(13)
    r.font.italic = italic
    return p

# TRANG BÌA
p_school = doc.add_paragraph()
p_school.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p_school.add_run("TRƯỜNG ĐẠI HỌC KỸ THUẬT - CÔNG NGHỆ CẦN THƠ\nKHOA CÔNG NGHỆ THÔNG TIN\n\n\n\n")
r.font.name = 'Times New Roman'
r.font.size = Pt(14)
r.font.bold = True

p_type = doc.add_paragraph()
p_type.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p_type.add_run("ĐỒ ÁN TỐT NGHIỆP\nNgành: Kỹ thuật phần mềm\n\n")
r.font.name = 'Times New Roman'
r.font.size = Pt(16)
r.font.bold = True

p_name = doc.add_paragraph()
p_name.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p_name.add_run("HỆ THỐNG QUẢN LÝ, CẤP PHÁT VÀ XÁC MINH VĂN BẰNG\nTRÊN NỀN TẢNG BLOCKCHAIN\n\n\n")
r.font.name = 'Times New Roman'
r.font.size = Pt(18)
r.font.bold = True
r.font.color.rgb = RGBColor(0, 51, 102)

p_info = doc.add_paragraph()
p_info.paragraph_format.line_spacing = 1.3
p_info.add_run("Cán bộ hướng dẫn:                                     Sinh viên thực hiện:\n").bold = True
p_info.add_run("ThS. Phạm Thị Thùy Linh                             Nguyễn Minh Nghĩa - MSSV: KTPM2311076\n")
p_info.add_run("                                                                    Võ Trường Khương - MSSV: KTPM2311039\n")
p_info.add_run("                                                                    Phạm Gia Khiêm - MSSV: KTPM2311036\n\n\n")
for r in p_info.runs:
    r.font.name = 'Times New Roman'
    r.font.size = Pt(13)

p_date = doc.add_paragraph()
p_date.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p_date.add_run("Cần Thơ, năm 2026")
r.font.name = 'Times New Roman'
r.font.size = Pt(13)
r.font.bold = True

doc.add_page_break()

# SƯỜN MỤC LỤC CHUẨN FORM ĐỒ ÁN 2
add_header("MỤC LỤC CHI TIẾT (CHUẨN 100% THEO FORM ĐỒ ÁN 2)", level=1)
add_para("Nhóm giữ nguyên cấu trúc 5 Chương của Đồ án 2, thay thế phần Hệ thống gợi ý / Tìm kiếm bằng công nghệ Blockchain, Smart Contract, Mạng IPFS và Cây Merkle:")

toc_doan2 = [
    ("LỜI CẢM ƠN", "Nghĩa"),
    ("LỜI NÓI ĐẦU", "Nghĩa"),
    ("MỤC LỤC", "Tự động"),
    ("DANH MỤC HÌNH ẢNH", "Tự động"),
    ("DANH MỤC BẢNG", "Tự động"),
    ("CHƯƠNG 1: TỔNG QUAN", "Nghĩa"),
    ("  1.1. Lý do chọn đề tài (Nạn bằng giả & nhu cầu chuyển đổi số)", "Nghĩa"),
    ("  1.2. Mục tiêu của đề tài (Toàn vẹn - Xác minh tức thì - Bảo mật)", "Nghĩa"),
    ("  1.3. Phạm vi của đề tài", "Nghĩa"),
    ("       1.3.1 Phạm vi nghiệp vụ (Quy trình quản lý, cấp phát, thu hồi văn bằng)", "Nghĩa"),
    ("       1.3.2 Phạm vi kỹ thuật và chức năng (Web Django, Mạng Sepolia, IPFS)", "Nghĩa"),
    ("CHƯƠNG 2: CƠ SỞ LÝ THUYẾT", "Khương & Khiêm"),
    ("  1. TỔNG QUAN VỀ CÔNG NGHỆ WEB FRONT-END (HTML5, CSS3, JavaScript, Tailwind)", "Nghĩa"),
    ("  2. NGÔN NGỮ LẬP TRÌNH BACK-END VÀ FRAMEWORK (Python, Django Framework)", "Nghĩa"),
    ("  3. MÔ HÌNH KIẾN TRÚC MVT / MVC (MODEL - VIEW - TEMPLATE)", "Nghĩa"),
    ("  4. HỆ QUẢN TRỊ CƠ SỞ DỮ LIỆU POSTGRESQL (Vai trò lưu trữ Off-Chain)", "Nghĩa"),
    ("  5. TỔNG QUAN VỀ CÔNG NGHỆ BLOCKCHAIN VÀ HỢP ĐỒNG THÔNG MINH", "Khương"),
    ("     5.1. Khái niệm Blockchain, Cơ chế đồng thuận và Mạng máy ảo Ethereum (EVM)", "Khương"),
    ("     5.2. Mạng thử nghiệm Ethereum Sepolia Testnet", "Khương"),
    ("     5.3. Hợp đồng thông minh (Smart Contract) và Ngôn ngữ lập trình Solidity", "Khương"),
    ("     5.4. Chuẩn Token định danh linh hồn Soulbound Token (ERC-5192 chống chuyển nhượng)", "Khương"),
    ("     5.5. Mạng lưu trữ phân tán IPFS (InterPlanetary File System) và mã băm CID", "Khương"),
    ("     [TÍCH HỢP TRẢ LỜI CÂU 1 & CÂU 4 CỦA CÔ: CSDL lưu trong và ngoài, lưu Merkle Root tiết kiệm 99.8% gas, IPFS]", "Khương"),
    ("  6. CƠ SỞ LÝ THUYẾT VỀ MẬT MÃ HỌC VÀ CẤU TRÚC CÂY MERKLE", "Khiêm"),
    ("     6.1. Hàm băm mật mã học (Keccak-256) và Hiệu ứng tuyết lở (Avalanche Effect)", "Khiêm"),
    ("     6.2. Cấu trúc Cây Merkle (Merkle Tree) và Thuật toán Merkle Proof O(logN)", "Khiêm"),
    ("     6.3. Thuật toán chuẩn hóa dữ liệu Canonicalization và cơ chế khóa cứng điểm GPA", "Khiêm"),
    ("  7. MÔI TRƯỜNG PHÁT TRIỂN VÀ CÔNG CỤ HỖ TRỢ", "Khương"),
    ("     7.1. Thư viện Web3.py và Trình biên dịch Remix IDE", "Khương"),
    ("     7.2. Ví điện tử MetaMask và Chuẩn xác thực SIWE (EIP-4361)", "Khương"),
    ("     7.3. Celery và Redis hỗ trợ đồng bộ giao dịch chạy nền", "Nghĩa"),
    ("CHƯƠNG 3: PHÂN TÍCH THIẾT KẾ", "Cả 3 người"),
    ("  1. PHÂN TÍCH ĐẶC TẢ, YÊU CẦU CỦA HỆ THỐNG", "Nghĩa"),
    ("     1.1. Phân tích hệ thống (Xác định vai trò của các Actor: Admin, Maker, Checker, Issuer, Sinh viên, Doanh nghiệp)", "Nghĩa"),
    ("     1.2. Mô tả hệ thống (Quy trình 4 mắt, cấp phát đợt/đơn lẻ, xác minh công khai)", "Nghĩa"),
    ("  2. THIẾT KẾ HỆ THỐNG", "Cả 3 người"),
    ("     2.1. Use case (Danh sách các Use case)", "Nghĩa"),
    ("     2.2. Xác định mối quan hệ giữa Actor và các Use case:", "Cả 3 người"),
    ("          2.2.1 Sơ đồ và Bảng mô tả Use Case của Sinh viên / Khách tra cứu (Khiêm)", "Khiêm"),
    ("          2.2.2 Sơ đồ và Bảng mô tả Use Case của Doanh nghiệp (Nghĩa)", "Nghĩa"),
    ("          2.2.3 Sơ đồ và Bảng mô tả Use Case của Cán bộ nhập liệu Maker (Nghĩa)", "Nghĩa"),
    ("          2.2.4 Sơ đồ và Bảng mô tả Use Case của Lãnh đạo duyệt Checker (Khiêm)", "Khiêm"),
    ("          2.2.5 Sơ đồ và Bảng mô tả Use Case của Cán bộ ký phát hành Issuer (Khiêm)", "Khiêm"),
    ("          2.2.6 Sơ đồ và Bảng mô tả Use Case của Quản trị viên Admin (Nghĩa)", "Nghĩa"),
    ("  3. CƠ SỞ DỮ LIỆU", "Nghĩa"),
    ("     3.1. Tổng quan kiến trúc lưu trữ lai (Hybrid Storage: On-Chain vs Off-Chain)", "Khương & Nghĩa"),
    ("     3.2. Lược đồ quan hệ thực thể (ERD PostgreSQL)", "Nghĩa"),
    ("     3.3. Chi tiết các bảng dữ liệu (User, Student, Degree, GraduationBatch, AuditLog, BlockchainTransaction...)", "Nghĩa"),
    ("  4. SƠ ĐỒ LỚP (CLASS DIAGRAM) BACKEND DJANGO", "Nghĩa"),
    ("  5. THIẾT KẾ SMART CONTRACT VÀ THUẬT TOÁN BẢO VỆ DỮ LIỆU", "Khương & Khiêm"),
    ("     5.1. Thiết kế Hợp đồng xác thực DegreeVerification.sol (Khương) -> [TRẢ LỜI CÂU 3]", "Khương"),
    ("     5.2. Thiết kế Hợp đồng bằng cấp điện tử DegreeSoulboundToken.sol (Khương) -> [TRẢ LỜI CÂU 3]", "Khương"),
    ("     5.3. Thiết kế Thuật toán Canonicalizer khóa cứng điểm số GPA (Khiêm) -> [TRẢ LỜI CÂU 5]", "Khiêm"),
    ("     5.4. Thiết kế Sơ đồ tuần tự Đăng nhập ví MetaMask SIWE (Khương)", "Khương"),
    ("     5.5. Thiết kế Sơ đồ tuần tự Xác minh văn bằng On-Chain (Khiêm)", "Khiêm"),
    ("CHƯƠNG 4: KẾT QUẢ", "Cả 3 người"),
    ("  1. KẾT QUẢ TRIỂN KHAI HỆ THỐNG WEBSITE (Chụp ảnh và mô tả chức năng từng hình như Đồ án 2)", "Cả 3 người"),
    ("     1.1. Giao diện người dùng / Sinh viên / Doanh nghiệp", "Khiêm"),
    ("          1.1.1 Giao diện Trang chủ Cổng tra cứu (Landing)", "Khiêm"),
    ("          1.1.2 Giao diện tra cứu văn bằng Hợp lệ (xanh lá)", "Khiêm"),
    ("          1.1.3 Giao diện tra cứu văn bằng Bị thu hồi (đỏ)", "Khiêm"),
    ("          1.1.4 Giao diện tra cứu Không tìm thấy dữ liệu (xám)", "Khiêm"),
    ("          1.1.5 Giao diện giải đố Captcha 3x3 chống cào dữ liệu", "Khiêm"),
    ("          1.1.6 Giao diện tra cứu Chứng nhận tốt nghiệp tạm thời", "Khiêm"),
    ("          1.1.7 Giao diện Cổng doanh nghiệp thẩm định hàng loạt", "Nghĩa"),
    ("          1.1.8 Giao diện Bản chứng thực điện tử PDF có mã QR", "Nghĩa"),
    ("          1.1.9 Giao diện Đăng nhập tài khoản & Đăng nhập ví MetaMask SIWE", "Khương"),
    ("          1.1.10 Giao diện Cổng thông tin sinh viên xem văn bằng", "Nghĩa"),
    ("          1.1.11 Giao diện sinh viên chia sẻ hồ sơ công khai (LinkedIn/CV)", "Nghĩa"),
    ("          1.1.12 Giao diện mở xem file PDF gốc qua IPFS Viewer", "Khương"),
    ("          1.1.13 Mẫu phôi bằng PDF Cử nhân, Kỹ sư, Chứng chỉ Tin học", "Khiêm"),
    ("     1.2. Giao diện Quản trị viên và Cán bộ nghiệp vụ", "Nghĩa"),
    ("          1.2.1 Giao diện Bảng điều khiển trung tâm Dashboard", "Nghĩa"),
    ("          1.2.2 Giao diện Quản lý danh sách sinh viên", "Nghĩa"),
    ("          1.2.3 Giao diện Form import sinh viên từ Excel có dropdown chọn loại bằng", "Nghĩa"),
    ("          1.2.4 Giao diện Lịch sử import và nút Hoàn tác (Rollback)", "Nghĩa"),
    ("          1.2.5 Giao diện Quản lý đợt tốt nghiệp", "Nghĩa"),
    ("          1.2.6 Giao diện Sổ Cái Văn Bằng Số", "Nghĩa"),
    ("          1.2.7 Giao diện Trình duyệt văn bằng đơn lẻ (Maker - Bước 1)", "Khiêm"),
    ("          1.2.8 Giao diện Phê duyệt & Cấp phôi On-Chain (Checker - Bước 2)", "Khiêm"),
    ("          1.2.9 Giao diện Ký phát hành văn bằng qua MetaMask (Issuer - Bước 3)", "Khương"),
    ("          1.2.10 Giao diện Xuất Sổ gốc chuẩn Thông tư 21/2019/TT-BGDĐT", "Nghĩa"),
    ("          1.2.11 Giao diện Quản lý và duyệt yêu cầu thu hồi văn bằng", "Khiêm"),
    ("          1.2.12 Giao diện Ký thu hồi văn bằng qua MetaMask", "Khương"),
    ("          1.2.13 Giao diện Nhật ký kiểm toán AuditLog", "Nghĩa"),
    ("          1.2.14 Giao diện Lịch sử giao dịch BlockchainTransaction", "Khương"),
    ("  2. KẾT QUẢ VẬN HÀNH BLOCKCHAIN VÀ THỰC NGHIỆM", "Khương & Khiêm"),
    ("     2.1. Triển khai Smart Contract trên mạng Ethereum Sepolia (Địa chỉ, Etherscan)", "Khương"),
    ("     2.2. Thống kê chi phí Gas và 9 loại Transaction (Gas Analytics) -> [TRẢ LỜI CÂU 2]", "Khương"),
    ("     2.3. Thực nghiệm kiểm chứng bảo vệ điểm số GPA (Tamper Test) -> [MINH CHỨNG CÂU 5]", "Khiêm"),
    ("     2.4. Thực nghiệm Cấp phát đơn lẻ vs Cấp phát theo đợt", "Khiêm"),
    ("CHƯƠNG 5: KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN", "Khiêm"),
    ("  1. KẾT QUẢ ĐẠT ĐƯỢC (1.1 Về mặt lý thuyết, 1.2 Về mặt ứng dụng thực tiễn)", "Khiêm"),
    ("  2. HẠN CHẾ CỦA HỆ THỐNG", "Khiêm"),
    ("  3. HƯỚNG PHÁT TRIỂN (Triển khai Mainnet, Consortium, Zero-Knowledge Proofs)", "Khiêm"),
    ("TÀI LIỆU THAM KHẢO", "Khương")
]

for item, author in toc_doan2:
    if item.startswith("CHƯƠNG") or item.startswith("LỜI") or item.startswith("MỤC") or item.startswith("DANH") or item.startswith("TÀI"):
        add_header(f"{item} ({author})", level=2)
    else:
        add_para(f"{item}  [{author}]")

# LƯU FILE
path_out = r"d:\doan\Bao_Cao_DATN_Theo_Form_Do_An_2.docx"
doc.save(path_out)
print(f"Saved to {path_out}")
