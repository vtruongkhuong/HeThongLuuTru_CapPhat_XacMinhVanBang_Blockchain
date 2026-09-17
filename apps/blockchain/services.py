import hashlib
import json

def generate_canonical_hash(degree_data: dict) -> str:
    """
    1. CANONICAL HASH (Mã băm chuẩn hóa cho từng văn bằng)
    Ép JSON xếp theo bảng chữ cái và xóa toàn bộ khoảng trắng thừa để băm chính xác tuyệt đối.
    """
    canonical_string = json.dumps(degree_data, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical_string.encode('utf-8')).hexdigest()

def build_merkle_root(hash_list: list) -> str:
    """
    2. MERKLE ROOT (Gom tất cả mã Hash của 1 đợt thành 1 mã duy nhất)
    Thuật toán đệ quy: Ghép cặp 2 mã hash cạnh nhau, băm lại, làm liên tục cho đến khi còn 1 mã (Root).
    """
    if not hash_list:
        return ""
    
    if len(hash_list) == 1:
        return hash_list[0]
        
    new_level = []
    for i in range(0, len(hash_list), 2):
        left = hash_list[i]
        right = hash_list[i+1] if (i + 1) < len(hash_list) else left
        
        combined = left + right
        new_hash = hashlib.sha256(combined.encode('utf-8')).hexdigest()
        new_level.append(new_hash)
        
    return build_merkle_root(new_level)