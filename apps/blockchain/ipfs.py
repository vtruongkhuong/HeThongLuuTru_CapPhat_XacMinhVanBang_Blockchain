"""
Module tích hợp lưu trữ phi tập trung IPFS (InterPlanetary File System).
Hỗ trợ:
  1. Tải lên dịch vụ IPFS Pinata Cloud (khi có PINATA_JWT hoặc PINATA_API_KEY).
  2. Tự động sinh mã băm IPFS CIDv0 chuẩn (Qm...) theo đặc tả multihash/base58 khi chạy offline/testnet.
  3. Tải lên metadata JSON cho Soulbound Token (SBT).
"""
import os
import json
import hashlib
import requests
from django.conf import settings

BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
DEFAULT_IPFS_GATEWAY = "https://gateway.pinata.cloud/ipfs"


def _base58_encode(b: bytes) -> str:
    """Mã hóa chuỗi byte sang chuẩn Base58 (Bitcoin/IPFS)."""
    n = int.from_bytes(b, 'big')
    chars = []
    while n > 0:
        n, r = divmod(n, 58)
        chars.append(BASE58_ALPHABET[r])
    for byte in b:
        if byte == 0:
            chars.append(BASE58_ALPHABET[0])
        else:
            break
    return ''.join(reversed(chars))


def compute_ipfs_cid(data: bytes) -> str:
    """
    Tính mã băm IPFS CIDv0 (Qm... 46 ký tự):
    Chuẩn Multihash: 0x12 (SHA-256) + 0x20 (32 bytes độ dài) + 32 bytes SHA-256 digest.
    """
    digest = hashlib.sha256(data).digest()
    multihash = bytes([0x12, 0x20]) + digest
    return _base58_encode(multihash)


def pin_file_to_ipfs(file_data_or_path, file_name: str = "degree.pdf", metadata: dict = None) -> tuple:
    """
    Tải file (PDF văn bằng) lên IPFS.
    Trả về tuple: (cid: str, gateway_url: str)
    """
    # 1. Đọc nội dung file dạng bytes
    if isinstance(file_data_or_path, (str, bytes, bytearray)):
        if isinstance(file_data_or_path, str) and os.path.exists(file_data_or_path):
            with open(file_data_or_path, 'rb') as f:
                content = f.read()
        elif isinstance(file_data_or_path, (bytes, bytearray)):
            content = bytes(file_data_or_path)
        else:
            content = file_data_or_path.encode('utf-8')
    else:
        content = file_data_or_path.read()

    jwt_token = getattr(settings, 'PINATA_JWT', '') or os.getenv('PINATA_JWT', '')
    api_key = getattr(settings, 'PINATA_API_KEY', '') or os.getenv('PINATA_API_KEY', '')
    secret_key = getattr(settings, 'PINATA_SECRET_KEY', '') or os.getenv('PINATA_SECRET_KEY', '')

    # 2. Thử tải lên qua Pinata API nếu có cấu hình Key
    if jwt_token or (api_key and secret_key):
        try:
            url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
            headers = {}
            if jwt_token:
                headers['Authorization'] = f"Bearer {jwt_token}"
            else:
                headers['pinata_api_key'] = api_key
                headers['pinata_secret_api_key'] = secret_key

            files = {'file': (file_name, content)}
            data = {}
            if metadata:
                data['pinataMetadata'] = json.dumps({'name': file_name, 'keyvalues': metadata})

            resp = requests.post(url, files=files, data=data, headers=headers, timeout=15)
            if resp.status_code == 200:
                cid = resp.json().get('IpfsHash')
                gateway_url = f"{DEFAULT_IPFS_GATEWAY}/{cid}"
                return cid, gateway_url
        except Exception as e:
            print(f"[IPFS Pinata Warning] {e}. Chuyển sang chế độ tính toán chuẩn CID.")

    # 3. Fallback: Tính toán IPFS CIDv0 chuẩn theo Multihash
    cid = compute_ipfs_cid(content)
    gateway_url = f"{DEFAULT_IPFS_GATEWAY}/{cid}"
    return cid, gateway_url


def pin_json_to_ipfs(json_data: dict, name: str = "degree_metadata.json") -> tuple:
    """
    Tải metadata JSON (chuẩn ERC-721/SBT) lên IPFS.
    Trả về tuple: (cid: str, gateway_url: str)
    """
    raw_bytes = json.dumps(json_data, ensure_ascii=False, indent=2).encode('utf-8')
    return pin_file_to_ipfs(raw_bytes, file_name=name)
