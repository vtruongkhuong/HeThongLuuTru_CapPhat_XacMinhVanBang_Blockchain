import os
import django
import sys

# Thiết lập môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from apps.degrees.canonicalizer import canonical_hash, HASH_VERSION
from apps.blockchain.services import build_merkle_tree, verify_merkle_proof

print("\n" + "=" * 75)
print("🎓 DEMO BẢO VỆ ĐIỂM SỐ BẰNG BLOCKCHAIN (CHỐNG SỬA ĐIỂM TRONG DATABASE)")
print("=" * 75)

# Giả lập dữ liệu sinh viên ban đầu
student_data_original = {
    "hash_version": HASH_VERSION,
    "credential_public_id": "b1b0c034-7c5b-4c07-9b25-055276e0b759",
    "student_code": "B210001",
    "full_name": "Nguyễn Văn An",
    "major_code": "7480201",
    "degree_type_code": "CN",
    "batch_name": "Đợt Tốt Nghiệp Khóa 2026",
    "classification": "Khá",
    "gpa_score": "2.85",  # Điểm GPA thực tế
    "issue_date": "2026-11-13"
}

hash_original = canonical_hash(student_data_original)
print("\n[BƯỚC 1 - CẤP PHÁT BAN ĐẦU]")
print(f"   Họ tên sinh viên   : {student_data_original['full_name']} (MSSV: {student_data_original['student_code']})")
print(f"   Điểm GPA ban đầu   : {student_data_original['gpa_score']} (Xếp loại: {student_data_original['classification']})")
print(f"   Mã băm gốc (Leaf)  : {hash_original}")

# Giả lập gom vào Merkle Tree cùng các sinh viên khác và chốt Merkle Root lên Smart Contract
other_leaves = ["0x" + "1" * 64, "0x" + "2" * 64, "0x" + "3" * 64]
all_leaves = [hash_original] + other_leaves
merkle_root_on_chain, levels = build_merkle_tree(all_leaves)
print(f"   Merkle Root On-Chain : {merkle_root_on_chain}")

# Lấy Merkle Proof cho sinh viên
from apps.blockchain.services import get_merkle_proof
proof = get_merkle_proof(all_leaves, 0)
is_valid_initial = verify_merkle_proof(hash_original, proof, merkle_root_on_chain)
print(f"   => Xác minh trên Smart Contract lúc này: {'✅ HỢP LỆ (100% Khớp)' if is_valid_initial else '❌ Thất bại'}")

print("\n" + "-" * 75)
print("🚨 [BƯỚC 2 - KẺ XẤU ĐỘT NHẬP CSDL POSTGRESQL SỬA ĐIỂM]")
print("   Kẻ xấu sửa: Điểm 2.85 (Khá) -> 3.85 (Xuất sắc) trực tiếp trong Database!")

student_data_tampered = dict(student_data_original)
student_data_tampered["gpa_score"] = "3.85"
student_data_tampered["classification"] = "Xuất sắc"

hash_tampered = canonical_hash(student_data_tampered)
print(f"   Mã băm sau khi sửa lén : {hash_tampered}")
print(f"   Nhận xét về mã băm    : Khác hoàn toàn so với mã gốc dù chỉ đổi điểm số!")

print("\n[BƯỚC 3 - HỆ THỐNG XÁC MINH / ĐỐI SOÁT VỚI SMART CONTRACT]")
is_valid_after_tampering = verify_merkle_proof(hash_tampered, proof, merkle_root_on_chain)

if not is_valid_after_tampering:
    print("   ❌ KẾT QUẢ: KHÔNG HỢP LỆ! (INVALID / GIAN LẬN)")
    print("   🛡️ HÀNG RÀO MẬT MÃ BLOCKCHAIN: Merkle Root trên Smart Contract không khớp!")
    print("   => Điểm số trong CSDL đã bị sửa đổi trái phép sau khi ký phát hành.")
else:
    print("   Lỗi: Không phát hiện được gian lận.")

print("=" * 75)
print("🎉 KẾT LUẬN: Blockchain KHÔNG CẦN lưu chữ '3.85', nhưng vẫn bảo vệ điểm số tuyệt đối 100%!")
print("=" * 75 + "\n")
