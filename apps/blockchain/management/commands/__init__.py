"""
Lệnh tự động đối soát dữ liệu (Reconcile Chain - H7).
Quét các đợt phát hành, kiểm tra Merkle Root và trạng thái thu hồi trên Blockchain.
"""
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from web3 import Web3

# Import từ các model hiện tại theo models_4.py và models_3.py
from apps.blockchain.models import IssuanceBatch
from apps.degrees.models import Degree

class Command(BaseCommand):
    help = "Đối soát dữ liệu văn bằng và Merkle Root giữa Database và Blockchain (Sepolia)."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("🚀 Bắt đầu quá trình đối soát dữ liệu (Reconcile Chain)..."))

        # 1. Khởi tạo kết nối Web3
        rpc_url = getattr(settings, 'WEB3_PROVIDER_URI', os.getenv('WEB3_PROVIDER_URI'))
        if not rpc_url:
            self.stdout.write(self.style.ERROR("❌ Lỗi: Chưa cấu hình WEB3_PROVIDER_URI trong .env"))
            return
            
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            self.stdout.write(self.style.ERROR(f"❌ Lỗi: Không thể kết nối tới RPC: {rpc_url}"))
            return

        contract_address = getattr(settings, 'CONTRACT_ADDRESS', os.getenv('CONTRACT_ADDRESS'))
        
        # Tạm thời dùng ABI rút gọn chứa getBatch và isRevoked để đối soát
        abi = [
            {
                "inputs": [{"internalType": "bytes32", "name": "batchId", "type": "bytes32"}],
                "name": "getBatch",
                "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}, {"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"internalType": "bytes32", "name": "batchId", "type": "bytes32"}, {"internalType": "bytes32", "name": "leaf", "type": "bytes32"}],
                "name": "isRevoked",
                "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        contract = w3.eth.contract(address=contract_address, abi=abi)
        
        # Lấy danh sách các đợt đã được ghi nhận trên chain
        batches = IssuanceBatch.objects.filter(status='CONFIRMED')
        error_found = False

        for batch in batches:
            self.stdout.write(f"🔄 Đang kiểm tra Đợt {batch.graduation_batch.name} (ID: {batch.id})...")
            
            # 2. Đối soát Merkle Root
            # Chuyển batch_id thành bytes32 
            # (Giả định: batch_id trên contract được lưu bằng ID của graduation_batch padding left 32 bytes)
            batch_id_bytes32 = batch.graduation_batch.id.to_bytes(32, byteorder='big')
            
            try:
                # Gọi hàm getBatch từ contract
                chain_root, count = contract.functions.getBatch(batch_id_bytes32).call()
                chain_root_hex = "0x" + chain_root.hex()
                
                db_root_hex = batch.merkle_root
                if not db_root_hex.startswith("0x"):
                    db_root_hex = "0x" + db_root_hex
                    
                if chain_root_hex.lower() != db_root_hex.lower():
                    self.stdout.write(self.style.ERROR(f"🚨 CẢNH BÁO BẢO MẬT: Merkle Root đợt '{batch.graduation_batch.name}' bị sai lệch!"))
                    self.stdout.write(self.style.WARNING(f"   DB Root:    {db_root_hex}"))
                    self.stdout.write(self.style.WARNING(f"   Chain Root: {chain_root_hex}"))
                    error_found = True
                else:
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Merkle Root khớp."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Lỗi khi đọc getBatch cho đợt {batch.id}: {str(e)}"))
                error_found = True
                continue

            # 3. Đối soát trạng thái thu hồi của từng văn bằng (isRevoked)
            degrees = Degree.objects.filter(batch=batch.graduation_batch)
            for degree in degrees:
                leaf_bytes32 = bytes.fromhex(degree.canonical_hash.replace('0x', ''))
                try:
                    chain_is_revoked = contract.functions.isRevoked(batch_id_bytes32, leaf_bytes32).call()
                    db_is_revoked = (degree.status == 'REVOKED')
                    
                    if chain_is_revoked != db_is_revoked:
                        self.stdout.write(self.style.ERROR(f"🚨 CẢNH BÁO: Trạng thái thu hồi của bằng {degree.credential_public_id} bị sai lệch!"))
                        self.stdout.write(self.style.WARNING(f"   DB Status: {'REVOKED' if db_is_revoked else 'ACTIVE'} | Chain Status: {'REVOKED' if chain_is_revoked else 'ACTIVE'}"))
                        error_found = True
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ Lỗi khi đọc isRevoked cho văn bằng {degree.id}: {str(e)}"))
                    error_found = True

        if not error_found:
            self.stdout.write(self.style.SUCCESS("✅ Đối soát hoàn tất! Toàn bộ dữ liệu khớp 100% với Blockchain."))
        else:
            self.stdout.write(self.style.ERROR("⚠️ Đối soát hoàn tất, phát hiện có dữ liệu sai lệch (Tampering)! Vui lòng kiểm tra lại log."))