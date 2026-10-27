"""
Chuẩn hóa dữ liệu văn bằng thành canonical JSON và tính leaf hash keccak256.
Muối duy nhất là credential_public_id (UUID cố định, không đổi) – đảm bảo
có thể tái tính hash bất kỳ lúc nào từ DB.
"""
import json
from web3 import Web3
HASH_VERSION = "1"
def make_leaf_data(degree) -> dict:
    """
    Trả về dict chuẩn hóa của 1 văn bằng.
    Thứ tự key không quan trọng vì canonical_hash sẽ sort_keys trước khi băm.
    """
    return {
        "hash_version": HASH_VERSION,
        "credential_public_id": str(degree.credential_public_id),
        "student_code": degree.student.student_code,
        "full_name": degree.student.full_name,
        "major_code": degree.student.major.code if degree.student.major else "",
        "degree_type_code": degree.degree_type.code if degree.degree_type else "",
        "batch_name": degree.batch.name,
        "classification": degree.classification or "",
        "issue_date": str(degree.issue_date) if degree.issue_date else "",
    }

def canonical_hash(leaf_data: dict) -> str:
    s = json.dumps(leaf_data, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return Web3.keccak(s.encode('utf-8')).hex()

def degree_leaf_hash(degree) -> str:
    return canonical_hash(make_leaf_data(degree))