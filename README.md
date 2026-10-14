# Hệ thống Quản lý, Cấp phát và Xác minh Văn bằng trên Blockchain

## 1. Yêu cầu môi trường
- **Python:** 3.10+
- **Cơ sở dữ liệu:** PostgreSQL (Sử dụng Cloud Database chung trên **Neon.tech**)
- **Hàng đợi xử lý ngầm:** Redis Server (port `6379`)
- **Trình duyệt:** Cài đặt sẵn tiện ích ví **MetaMask** (chuyển sang mạng **Sepolia Testnet**)

---

## 2. Hướng dẫn cài đặt từ đầu

### Bước 1: Clone dự án và tạo môi trường ảo
```bash
git clone <url_repository>
cd HeThongLuuTru_CapPhat_XacMinhVanBang_Blockchain
python -m venv venv

# Kích hoạt môi trường ảo trên Windows:
venv\Scripts\activate