"""Hàm tiện ích dùng chung cho nhiều app."""
import hashlib
import secrets
import unicodedata


def slugify_vn(text: str) -> str:
    """Chuyển chuỗi tiếng Việt có dấu thành slug không dấu, dùng cho mã sinh viên/tên file."""
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = text.lower().strip()
    text = '-'.join(text.split())
    return text


def sha256_hex(data: bytes) -> str:
    """Băm SHA-256, trả về chuỗi hex — dùng chung cho canonicalizer và verification."""
    return hashlib.sha256(data).hexdigest()


def generate_credential_id() -> str:
    """
    Sinh mã định danh văn bằng duy nhất, dùng để tra cứu công khai (QR code, URL verify).
    Format: VB-<8 ký tự ngẫu nhiên viết hoa>, dễ đọc, khó đoán.
    """
    token = secrets.token_hex(4).upper()
    return f"VB-{token}"


def mask_wallet_address(address: str, keep: int = 4) -> str:
    """Che bớt địa chỉ ví, chỉ hiện đầu/cuối — dùng khi hiển thị lên UI cho gọn."""
    if not address or len(address) <= keep * 2 + 2:
        return address
    return f"{address[:keep + 2]}...{address[-keep:]}"
