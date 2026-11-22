# HƯỚNG DẪN SỬ DỤNG DỮ LIỆU DEMO BẢO VỆ ĐỒ ÁN (Task 14 - Khương)

Thư mục này chứa 3 file PDF mẫu đại diện cho 3 kịch bản kiểm định thực tế của Nhà tuyển dụng / Hội đồng đánh giá:

---

### 1. `01_van_bang_hop_le.pdf` (VĂN BẰNG HỢP LỆ)
* **Sinh viên:** Võ Minh Em (`SV005`)
* **Loại bằng:** Bằng Kỹ sư Chính quy - Kỹ thuật phần mềm
* **Số hiệu:** `CTUT-2026-000001`
* **Trạng thái Blockchain:** `ISSUED` (Đã phát hành On-Chain Sepolia)
* **Kịch bản Demo:**
  - Kéo thả file PDF này vào chức năng kiểm định hoặc nhập số hiệu / mã hash vào API.
  - **Kết quả kỳ vọng:** Hiển thị huy hiệu xanh **VERIFIED (HỢP LỆ)**, có đầy đủ TxHash, Merkle Root, link Etherscan và mã IPFS CID.

---

### 2. `02_van_bang_gia_mao.pdf` (VĂN BẰNG GIẢ MẠO / SỬA ĐỔI)
* **Sinh viên:** Lê Giả Mạo (`SV999`)
* **Loại bằng:** Bằng Kỹ sư Chính quy
* **Số hiệu:** `CTUT-2026-999999`
* **Trạng thái Blockchain:** `TAMPERED / NOT_FOUND` (Không tồn tại trên sổ cái Blockchain hoặc hash bị sai lệch)
* **Kịch bản Demo:**
  - Kéo thả file PDF này vào chức năng thẩm định tuyển dụng.
  - **Kết quả kỳ vọng:** Hệ thống cảnh báo đỏ **TAMPERED / KHÔNG TÌM THẤY**, ngăn chặn gian lận hồ sơ ứng viên.

---

### 3. `03_van_bang_thu_hoi.pdf` (VĂN BẰNG ĐÃ BỊ THU HỒI)
* **Sinh viên:** Trần Thị Thu Hồi (`SV002`)
* **Loại bằng:** Bằng Cử nhân
* **Số hiệu:** `CTUT-2026-000002`
* **Trạng thái Blockchain:** `REVOKED` (Đã bị thu hồi trên Smart Contract theo Quyết định kỷ luật)
* **Kịch bản Demo:**
  - Tra cứu số hiệu hoặc quét file PDF này.
  - **Kết quả kỳ vọng:** Hệ thống hiển thị trạng thái cam/đỏ **REVOKED (ĐÃ BỊ THU HỒI)**, nêu rõ lý do kỷ luật và thời điểm thu hồi theo quy trình 4-Eyes Principle.

---

### 4. Dữ liệu tài khoản Doanh nghiệp API Key:
* **Tên doanh nghiệp:** Tập Đoàn Công Nghệ FPT - Ban Tuyển Dụng
* **API Key:** `4397dc03eec1bbc03d28b37c81540f537e072324af958bb7dd74acde8699da11`
* **Swagger UI:** `http://127.0.0.1:8000/api/docs/`
