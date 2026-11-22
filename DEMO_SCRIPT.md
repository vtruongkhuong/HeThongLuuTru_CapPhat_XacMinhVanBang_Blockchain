# KỊCH BẢN THUYẾT TRÌNH & DEMO ĐỒ ÁN TỐT NGHIỆP (10 PHÚT)
**Đề Tài:** Hệ Thống Quản Lý, Cấp Phát & Xác Minh Văn Bằng Số Trên Chuỗi Khối Ethereum Sepolia
**Nhóm Thực Hiện:** Nguyễn Minh Nghĩa - Võ Trường Khương - Phạm Quốc Khiêm
**Chuyên Ngành:** Kỹ thuật Phần mềm (KTPM) - Đại học Kỹ thuật - Công nghệ Cần Thơ (CTUT)

---

## TỔNG QUAN PHÂN BỔ THỜI GIAN (10 PHÚT)

| Phút | Phần Thuyết Trình | Hành Động Trên Hệ Thống / URL | Người Phụ Trách |
|:---:|---|---|:---:|
| **00:00 - 02:00** | **Đặt vấn đề & So sánh quy trình** | Mở Trang chủ: `http://localhost:8000/` | Trình bày chung |
| **02:00 - 03:00** | **Admin: Quản lý & Import dữ liệu** | `http://localhost:8000/admin/` | Admin |
| **03:00 - 04:00** | **Blockchain Hub: Phát hành On-Chain** | `http://localhost:8000/admin/blockchain/transactions/` | Admin / Kỹ thuật |
| **04:00 - 05:30** | **Cổng Sinh viên & Chia sẻ CV tuyển dụng** | `http://localhost:8000/portal/dashboard/` | Sinh viên (Nghĩa) |
| **05:30 - 07:30** | **Doanh nghiệp Thẩm định Hàng loạt 3 Case** | `http://localhost:8000/verify/doanh-nghiep/` | Doanh nghiệp / HR |
| **07:30 - 08:30** | **Tra cứu Công khai & Timeline Audit Trail** | `http://localhost:8000/verify/tracuu/?q=KTPM2311076` | Kiểm toán viên |
| **08:30 - 09:30** | **Dashboard Báo cáo & Tối ưu hóa** | `http://localhost:8000/report/` | Báo cáo số liệu |
| **09:30 - 10:00** | **Tổng kết & Sẵn sàng Q&A Hội đồng** | Trả lời bộ câu hỏi kỹ thuật chuyên sâu | Toàn nhóm |

---

## KỊCH BẢN CHI TIẾT TỪNG PHÚT

### ⏱ PHÚT 00:00 - 02:00 | ĐẶT VẤN ĐỀ & SO SÁNH QUY TRÌNH
* **Màn hình hiển thị:** [Trang chủ Cổng Tra cứu](http://localhost:8000/)
* **Lời nói thuyết minh:**
  > *"Kính thưa quý thầy cô trong Hội đồng, hiện nay quy trình xác minh văn bằng nhân sự truyền thống mất từ **3 đến 5 ngày làm việc**, phụ thuộc vào văn bản giấy tờ, gọi điện và rất dễ bị làm giả bằng công nghệ chỉnh sửa hình ảnh hiện đại.*
  > *Hệ thống của nhóm em giải quyết triệt để bài toán này bằng cách kết hợp **Cây Merkle Tree (RFC 6962)** và **Smart Contract trên Ethereum Sepolia Testnet**.*
  > *Thay vì 3-5 ngày, doanh nghiệp chỉ mất **~3 giây** để đối soát tính toàn vẹn 100% của văn bằng mà không thể bị làm giả."*
* **Thao tác:** Cuộn chuột xuống khối *"So Sánh Quy Trình Trước & Sau Blockchain"* và *"Kiến Trúc Mật Mã 4 Lớp"* trên trang chủ để chỉ trực quan cho thầy cô.

---

### ⏱ PHÚT 02:00 - 03:00 | ADMIN: QUẢN LÝ DỮ LIỆU & QUY TRÌNH BỐN MẮT
* **Màn hình hiển thị:** [Trang Governance Workflow Hub Admin](http://localhost:8000/admin/)
* **Lời nói thuyết minh:**
  > *"Hệ thống áp dụng nghiêm ngặt nguyên tắc quản trị **Bốn mắt (Four-eyes principle)**: Cán bộ tạo phôi không thể tự ý phát hành. Mọi hồ sơ tốt nghiệp phải qua các bước: Khởi tạo $\to$ Thẩm định $\to$ Phê duyệt $\to$ Đóng dấu Merkle Tree $\to$ Phát hành On-Chain."*
* **Thao tác:**
  - Bấm vào Bước 1: Xem danh sách sinh viên hoặc Import Excel.
  - Bấm vào Bước 2: Xem đợt tốt nghiệp đã khóa sổ.

---

### ⏱ PHÚT 03:00 - 04:00 | PHÁT HÀNH BLOCKCHAIN & TX EXPLORER
* **Màn hình hiển thị:** [Blockchain TX Explorer Mini](http://localhost:8000/admin/blockchain/transactions/)
* **Lời nói thuyết minh:**
  > *"Khi phát hành một đợt tốt nghiệp gồm hàng trăm sinh viên, thay vì gửi hàng trăm transaction riêng lẻ gây tốn kém gas, hệ thống tính toán **Merkle Root** gom toàn bộ vào đúng 1 giao dịch On-Chain duy nhất.*
  > *Tại trang Blockchain TX Explorer, quản trị viên có thể theo dõi mã giao dịch TxHash, số khối Block number, lượng gas tiêu thụ và mở thẳng liên kết trên Sepolia Etherscan."*
* **Thao tác:** Bấm mở 1 link `TxHash` để chứng minh giao dịch thật trên mạng Etherscan Sepolia.

---

### ⏱ PHÚT 04:00 - 05:30 | CỔNG SINH VIÊN (STUDENT PORTAL) & CHIA SẺ CV
* **Màn hình hiển thị:** [Cổng Sinh viên](http://localhost:8000/portal/dashboard/) (Đăng nhập tài khoản `nghia`)
* **Lời nói thuyết minh:**
  > *"Sinh viên có thể quản lý tập trung toàn bộ văn bằng ĐH và chứng chỉ CNTT. Tại đây, sinh viên có thể:*
  > *1. Xem và tải **Bản Giấy Chứng Thực Điện Tử (PDF)** chuẩn mẫu Bộ GD&ĐT có con dấu bảo mật Blockchain.*
  > *2. Tải trực tiếp **Mã QR Code độ nét cao** để dán vào hồ sơ giấy.*
  > *3. **Tạo Link Chia Sẻ CV bảo mật**: Cho phép sinh viên cài đặt thời hạn 1/7/14/30 ngày, đặt **mật khẩu bảo vệ**, và **giới hạn số lượt xem tối đa** để chống lộ thông tin cá nhân."*
* **Thao tác:**
  - Bấm nút *"Tải mã QR Code"* $\to$ tải file PNG về máy.
  - Bấm nút *"Tạo liên kết chia sẻ CV"* $\to$ chọn 14 ngày, nhập mật khẩu demo `123456`, giới hạn 5 lượt xem $\to$ Tạo link.
  - Mở tab ẩn danh dán link vào: màn hình yêu cầu nhập mã PIN $\to$ nhập `123456` $\to$ mở khóa thành công, đồng hồ Countdown thời gian thực đang đếm lùi.

---

### ⏱ PHÚT 05:30 - 07:30 | DOANH NGHIỆP THẨM ĐỊNH HÀNG LOẠT (3 TRẠNG THÁI DEMO)
* **Màn hình hiển thị:** [Cổng Doanh nghiệp](http://localhost:8000/verify/doanh-nghiep/)
* **Lời nói thuyết minh:**
  > *"Đây là tính năng đột phá nhất dành cho Phòng Nhân sự (HR): Thay vì kiểm tra từng người, HR kéo thả cùng lúc 20-50 tệp PDF văn bằng ứng viên vào khu vực Dropzone.*
  > *Hệ thống tự động tính mã băm SHA-256 và đối soát trực tiếp với Merkle Tree trên Smart Contract, phân loại chính xác 3 trạng thái:"*
* **Thao tác:**
  - Kéo thả file PDF văn bằng hợp lệ $\to$ Hệ thống báo **Xanh lá: HỢP LỆ VÀ TOÀN VẸN (100%)**.
  - Kéo thả file PDF đã sửa điểm/tên $\to$ Hệ thống báo **Đỏ: NGHI VẤN SỬA ĐỔI / KHÔNG TRÙNG KHỚP MẬT MÃ**.
  - Kéo thả văn bằng bị trường thu hồi $\to$ Hệ thống báo **Cam: VĂN BẰNG ĐÃ BỊ THU HỒI ON-CHAIN**.
  - Bấm nút *"Xuất Báo Cáo Thẩm Định Excel (.xlsx)"* $\to$ mở file Excel tải về cho hội đồng xem bảng kết quả đối soát chuyên nghiệp.

---

### ⏱ PHÚT 07:30 - 08:30 | TRA CỨU CÔNG KHAI & TIMELINE AUDIT TRAIL
* **Màn hình hiển thị:** [Kết quả tra cứu công khai KTPM2311076](http://localhost:8000/verify/tracuu/?q=KTPM2311076)
* **Lời nói thuyết minh:**
  > *"Trang tra cứu công khai cung cấp **Timeline Vòng đời Văn bằng (Lifecycle Audit Trail)** gồm 4 mốc thời gian minh bạch: từ thời điểm sinh viên tốt nghiệp, phê duyệt Four-eyes, băm Merkle Tree và đóng dấu Smart Contract.*
  > *Sinh viên có thể lấy mã **Badge SVG nhúng động** để gắn trực tiếp vào CV trực tuyến hoặc LinkedIn."*
* **Thao tác:** Cuộn xem 4 mốc timeline và copy mã nhúng Badge SVG.

---

### ⏱ PHÚT 08:30 - 09:30 | DASHBOARD BÁO CÁO THỐNG KÊ TỔNG THỂ
* **Màn hình hiển thị:** [Dashboard Báo cáo](http://localhost:8000/report/)
* **Lời nói thuyết minh:**
  > *"Ban giám hiệu nhà trường có thể theo dõi toàn bộ số liệu: Cơ cấu xếp loại tốt nghiệp (Biểu đồ Donut), biến động cấp phát theo năm (Biểu đồ Bar), lưu lượng xác minh trong 7 ngày gần nhất (Biểu đồ Line), và bảng đối soát đợt phát hành."*

---

### ⏱ PHÚT 09:30 - 10:00 | TỔNG KẾT & BỘ CÂU HỎI Q&A DỰ PHÒNG

#### Câu 1: Tại sao không lưu toàn bộ dữ liệu sinh viên lên Blockchain mà phải dùng Merkle Tree?
> **Trả lời:** *"Dạ thưa thầy/cô, có 2 lý do cốt lõi:*
> *1. **Chi phí Gas:** Lưu chuỗi dữ liệu lớn trên Ethereum rất đắt đỏ. Merkle Tree nén $N$ văn bằng thành đúng 1 Root Hash 32 bytes ($O(1)$ on-chain storage).*
> *2. **Bảo mật quyền riêng tư (Privacy/GDPR):** Blockchain là sổ cái công khai vĩnh viễn, không được xóa. Nếu ghi tên, CCCD sinh viên lên chain thì ai cũng đọc được và vi phạm quyền được quên (Right to be forgotten). Nhóm em chỉ lưu Root Hash đại diện, thông tin cá nhân vẫn nằm an toàn dưới quyền kiểm soát của trường."*

#### Câu 2: Nếu Server trường bị tắt mạng thì nhà tuyển dụng có xác minh được không?
> **Trả lời:** *"Dạ hoàn toàn được. Sinh viên có thể tải **Gói xác minh độc lập (JSON Verification Package)** chứa đầy đủ Merkle Leaf, Proof Path và địa chỉ Smart Contract. Nhà tuyển dụng dùng công cụ Client độc lập gọi trực tiếp vào node mạng Sepolia công khai để verify hàm `verifyProof()` mà không phụ thuộc vào server nhà trường."*

#### Câu 3: Làm sao phát hiện văn bằng bị thu hồi?
> **Trả lời:** *"Khi trường ra quyết định thu hồi, hàm `revokeDegree()` trên Smart Contract sẽ cập nhật trạng thái của mã băm lá đó thành revoked. Dù kẻ gian có giữ file PDF thật hay chứng thực cũ thì khi đối soát on-chain, Smart Contract sẽ lập tức trả về `isRevoked = true`."*
