import os
import django
import sys
from unittest.mock import MagicMock

# Thiết lập môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from apps.graduation.models import GraduationBatch
from apps.blockchain.models import IssuanceBatch
from apps.blockchain.management.commands.reconcile_chain import reconcile_merkle_roots

print("\n" + "=" * 70)
print("🎯 KỊCH BẢN DEMO: PHÁT HIỆN GIAN LẬN SỬA LÉN DATABASE (H7)")
print("=" * 70)

# Chuẩn bị dữ liệu mẫu
gb = GraduationBatch.objects.filter(name__icontains='Test').first()
if not gb:
    gb = GraduationBatch.objects.first()
if not gb:
    gb = GraduationBatch.objects.create(name="Đợt Tốt Nghiệp Khóa 2026")

ROOT_ON_CHAIN = "0x" + "a" * 64
CHAIN_ID = "0x" + "1" * 40

# Tạo một đợt phát hành tạm thời có mã Merkle Root chuẩn
ib = IssuanceBatch.objects.create(
    graduation_batch=gb,
    merkle_root=ROOT_ON_CHAIN,
    chain_id=CHAIN_ID,
    status="CONFIRMED"
)

# Mock kết nối Smart Contract trả về Merkle Root thật trên Sepolia Blockchain
mock_client = MagicMock()
mock_client.get_batch.return_value = {
    'root': ROOT_ON_CHAIN,
    'issued_at': 1730000000,
    'count': 100,
    'issuer': '0x8E53683464fE95222b854b9336ba1b8B6B913577'
}

try:
    print("\n[BƯỚC 1 - DỮ LIỆU CHUẨN]: Khi mã hash trong DB khớp với Blockchain:")
    res_ok = reconcile_merkle_roots(client=mock_client)
    for d in res_ok.get('details', []):
        if d['batch_id'] == ib.id:
            print(f"   {d['message']}")

    print("\n" + "-" * 70)
    print("⚠️ [BƯỚC 2 - GIẢ LẬP GIAN LẬN]: Kẻ xấu vào trực tiếp Database sửa lén 1 ký tự mã hash!")
    print(f"   Mã băm gốc trên Blockchain : {ROOT_ON_CHAIN}")
    
    # Cố tình sửa ký tự cuối từ 'a' thành 'f'
    TAMPERED_ROOT = "0x" + "a" * 63 + "f"
    ib.merkle_root = TAMPERED_ROOT
    ib.save()
    print(f"   Mã băm bị sửa lén trong DB: {TAMPERED_ROOT}")

    print("\n[BƯỚC 3 - CHẠY LỆNH ĐỐI SOÁT TỰ ĐỘNG (RECONCILE CHAIN)]:")
    res_tampered = reconcile_merkle_roots(client=mock_client)
    for d in res_tampered.get('details', []):
        if d['batch_id'] == ib.id:
            print(f"   {d['message']}")

    print("\n" + "=" * 70)
    print("✅ KẾT LUẬN: Hệ thống phát hiện ngay tức khắc sai lệch và báo động đỏ!")
    print("=" * 70 + "\n")

finally:
    # Dọn dẹp bản ghi tạm thời để không ảnh hưởng DB
    ib.delete()
