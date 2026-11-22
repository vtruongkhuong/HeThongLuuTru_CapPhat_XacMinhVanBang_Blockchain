# Hệ Thống Quản Lý, Cấp Phát & Xác Minh Văn Bằng Số Trên Blockchain

Hệ thống quản lý, cấp phát và thẩm định văn bằng, chứng chỉ đại học ứng dụng công nghệ Chuỗi khối (**Ethereum Sepolia Testnet**), Cấu trúc cây mật mã (**Merkle Tree RFC 6962**), và Lưu trữ tệp phân tán (**IPFS**).

---

## 1. Giới Thiệu Đề Tài & Bài Toán Giải Quyết

* **Thực trạng:** Quy trình xác minh văn bằng nhân sự truyền thống tốn từ 3–5 ngày làm việc, phụ thuộc vào bản sao công chứng và xác nhận qua đường bưu điện hoặc email; dễ bị làm giả bằng kỹ thuật đồ họa tinh vi.
* **Giải pháp:** 
  - Toàn bộ dữ liệu văn bằng và tệp PDF gốc được băm chuẩn hóa (**Keccak-256 & SHA-256**).
  - Thuật toán **Cây Merkle Tree** gom hàng ngàn văn bằng thành **đúng 1 Merkle Root (32 bytes)** đóng dấu lên Smart Contract, tối ưu hóa hơn 98% chi phí gas on-chain.
  - Doanh nghiệp thẩm định hàng loạt hồ sơ ứng viên chỉ mất **~3 giây**, độ chính xác tuyệt đối và không thể làm giả.

---

## 2. Kiến Trúc Mật Mã 4 Lớp (4-Layer Cryptographic Architecture)

```
┌─────────────────────────────────────────────────────────────┐
│ TẦNG 4: ON-CHAIN SMART CONTRACT (Sepolia Testnet 11155111)  │
│ - Lưu Merkle Root bất biến, kiểm tra trạng thái thu hồi      │
└──────────────────────────────▲──────────────────────────────┘
                               │ Merkle Root (32 bytes)
┌──────────────────────────────┴──────────────────────────────┐
│ TẦNG 3: CÂY MERKLE TREE RFC 6962 (Keccak-256 Pairing)       │
│ - Gom băm các Leaf Hash, sinh Audit Proof Path O(log N)     │
└──────────────────────────────▲──────────────────────────────┘
                               │ Leaf Hash (canonical_hash)
┌──────────────────────────────┴──────────────────────────────┐
│ TẦNG 2: PHÂN TÁN TỆP IPFS (InterPlanetary File System)      │
│ - Lưu trữ bản phôi PDF gốc, truy cập qua CID nội dung độc bản│
└──────────────────────────────▲──────────────────────────────┘
                               │ Canonical JSON & File Bytes
┌──────────────────────────────┴──────────────────────────────┐
│ TẦNG 1: CHUẨN HÓA MẬT MÃ (Keccak-256 & SHA-256)             │
│ - Băm dữ liệu sinh viên + Thông tư 21/2019/TT-BGDĐT         │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Danh Sách Tính Năng Cốt Lõi (20 Features)

### 🎓 Cổng Sinh Viên (Student Portal)
- [x] Quản lý tập trung 2 khu vực: Văn bằng Đại học chính quy và Chứng chỉ Tin học / CNTT.
- [x] Tải Bản Giấy Chứng Thực Điện Tử (PDF) chuẩn font Unicode tiếng Việt và con dấu Blockchain.
- [x] Tải Mã QR Code độ nét cao trực tiếp về máy dạng ảnh `.png`.
- [x] Tải Gói xác minh độc lập (.json) chứa Merkle Proof để đối soát offline.
- [x] Tạo Link chia sẻ CV xin việc có thời hạn (1, 7, 14, 30 ngày), mật khẩu bảo vệ và giới hạn lượt xem.
- [x] Trang xem hồ sơ công khai dành cho HR: Đồng hồ Countdown thời gian thực, huy hiệu chính chủ, nút chia sẻ LinkedIn.
- [x] Nhúng Huy hiệu Xác thực Blockchain SVG động (`/verify/badge/<uuid>.svg`) vào CV / Portfolio.

### 🏢 Cổng Doanh Nghiệp & Thẩm Định Hàng Loạt
- [x] Khu vực kéo thả (Drag & Drop) tải cùng lúc 20–50 tệp PDF văn bằng ứng viên.
- [x] Phân loại tức thì 4 trạng thái: Hợp lệ, Bị thu hồi, Nghi vấn sửa đổi (sai hàm băm), Không tìm thấy.
- [x] Xuất Báo cáo Thẩm định Nhân sự ra tệp Microsoft Excel (`.xlsx`) chỉ với 1 click.

### 🔍 Cổng Tra Cứu Công Khai (Public Verification)
- [x] Tra cứu đa năng: MSSV, Số hiệu văn bằng, Số vào sổ, Mã CCCD, UUID, hoặc Hash.
- [x] Quét mã QR trực tiếp qua Camera thiết bị trên phôi bằng giấy.
- [x] Timeline Vòng đời Văn bằng (Lifecycle Audit Trail): Khởi tạo $\to$ Duyệt Four-eyes $\to$ Băm Merkle $\to$ Smart Contract.
- [x] Khối so sánh quy trình Trước & Sau Blockchain.

### ⚙️ Quản Trị & Vận Hành On-Chain (Admin Hub)
- [x] Governance Workflow Hub với quy trình 4 bước chuẩn mực.
- [x] Nguyên tắc Bốn Mắt (Four-eyes principle): Phân quyền người tạo phôi và người duyệt riêng biệt.
- [x] Import danh sách sinh viên hàng loạt từ tệp Excel.
- [x] Cấp bằng đơn lẻ và tự động sinh số hiệu chuẩn Thông tư 21/2019/TT-BGDĐT.
- [x] Blockchain Transaction Explorer Mini: Giám sát mã TxHash, Gas used, Block number trên Sepolia.
- [x] Dashboard Báo cáo Thống kê: Biểu đồ Donut xếp loại, Bar chart theo năm, Line chart 7 ngày (Chart.js).

---

## 4. Bảng Tra Cứu API Endpoints

| Phương Thức | Tuyến Đường (Endpoint) | Quyền Truy Cập | Mục Đích |
|:---:|---|:---:|---|
| `GET` | `/` | Công khai | Cổng tra cứu văn bằng chính thức & QR Scanner |
| `GET` | `/verify/tracuu/?q=<query>` | Công khai | Kết quả xác minh chi tiết văn bằng & Timeline |
| `GET` | `/verify/doanh-nghiep/` | Công khai | Cổng Doanh nghiệp thẩm định hàng loạt |
| `POST`| `/verify/doanh-nghiep/` | Công khai | Xử lý đối soát batch file PDF & Xuất Excel |
| `GET` | `/verify/badge/<uuid>.svg` | Công khai | Trả về ảnh vector SVG động trạng thái bằng cấp |
| `GET` | `/verify/chung-thuc-pdf/<id>/` | Công khai | Xuất file PDF Giấy Chứng Thực Điện Tử |
| `GET` | `/portal/dashboard/` | Sinh viên | Bảng điều khiển quản lý văn bằng của sinh viên |
| `POST`| `/portal/tao-link-chia-se/` | Sinh viên | Tạo link chia sẻ CV có mật khẩu & thời hạn |
| `GET` | `/portal/cv/<token>/` | Công khai | Trang xem hồ sơ ứng viên dành cho Nhà tuyển dụng |
| `GET` | `/admin/blockchain/transactions/` | Staff / Admin | Blockchain Transaction Explorer |
| `GET` | `/report/` | Staff / Admin | Dashboard thống kê phân tích số liệu |

---

## 5. Thông Số Smart Contract (Ethereum Sepolia)

* **Mạng thử nghiệm:** Ethereum Sepolia Testnet
* **Chain ID:** `11155111`
* **Địa chỉ Smart Contract:** `0x8E53683464fE95222b854b9336ba1b8B6B913577`
* **Trình khám phá chuỗi khối:** [Sepolia Etherscan Contract](https://sepolia.etherscan.io/address/0x8E53683464fE95222b854b9336ba1b8B6B913577)
* **Các hàm chính trong Solidity:**
  - `issueBatch(bytes32 root, uint256 batchId)`: Ghi nhận Merkle Root của đợt tốt nghiệp.
  - `verifyDegree(bytes32 leaf, bytes32[] proof, uint256 batchId)`: Xác minh một chiếc lá văn bằng có thuộc Merkle Root hợp lệ hay không.
  - `revokeDegree(bytes32 leaf)`: Thu hồi văn bằng trên chuỗi khối.

---

## 6. Yêu Cầu Môi Trường & Cài Đặt

### Bước 1: Chuẩn bị môi trường
- Python 3.10 trở lên.
- Cài đặt Git.

### Bước 2: Clone dự án và khởi tạo môi trường ảo
```bash
git clone https://github.com/vtruongkhuong/HeThongLuuTru_CapPhat_XacMinhVanBang_Blockchain.git
cd HeThongLuuTru_CapPhat_XacMinhVanBang_Blockchain

python -m venv venv
# Kích hoạt trên Windows:
venv\Scripts\activate
# Kích hoạt trên Linux/macOS:
source venv/bin/activate
```

### Bước 3: Cài đặt thư viện phụ thuộc
```bash
pip install -r requirements.txt
```

### Bước 4: Thực thi di chuyển cơ sở dữ liệu (Migrations)
```bash
python manage.py migrate
```

### Bước 5: Chạy máy chủ phát triển (Development Server)
```bash
python manage.py runserver 0.0.0.0:8000
```
Truy cập hệ thống tại: `http://localhost:8000/`

---

## 7. Kiểm Thử Tự Động (Automated Testing)

Dự án tích hợp bộ kiểm thử tự động toàn diện:
```bash
python manage.py test tests
```
*Kết quả:* **25/25 unit tests PASSED (100% OK)**.

---

## 8. Thành Viên Thực Hiện

* **Nguyễn Minh Nghĩa** (MSSV: `KTPM2311076`) - Frontend & Portals UX/UI, Merkle Proof, Share Link, PDF Certification.
* **Võ Trường Khương** (`vtruongkhuong`) - Blockchain Core, Smart Contract Solidity, REST API & IPFS.
* **Phạm Quốc Khiêm** (`pzakhim-12`) - Reporting Analytics, HR Sessions & Notifications.

*Đại học Kỹ thuật - Công nghệ Cần Thơ (CTUT) — Niên khóa 2023 - 2026.*
