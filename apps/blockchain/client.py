import json
from web3 import Web3
from django.conf import settings
from .models import BlockchainTransaction

class BlockchainClient:
    def __init__(self):
        # 1. Kết nối tới mạng Sepolia thông qua biến môi trường
        self.w3 = Web3(Web3.HTTPProvider(settings.WEB3_PROVIDER_URL))
        
        # 2. Đọc file ABI (Từ điển để Python hiểu Smart Contract)
        with open('apps/blockchain/contracts_abi/DegreeVerification.json') as f:
            abi = json.load(f)
            
        # 3. Khởi tạo Contract
        self.contract = self.w3.eth.contract(address=settings.CONTRACT_ADDRESS, abi=abi)

    def publish_merkle_root(self, issuance_batch):
        """Hàm nhận IssuanceBatch và đẩy merkle_root lên Blockchain"""
        
        if not self.w3.is_connected():
            raise Exception("Lỗi: Không thể kết nối với mạng Blockchain!")

        # Lấy địa chỉ ví tự động từ Private Key
        account = self.w3.eth.account.from_key(settings.ISSUER_PRIVATE_KEY)
        wallet_address = account.address

        # 1. Khởi tạo giao dịch (Gọi hàm storeMerkleRoot đã viết bên Solidity)
        tx = self.contract.functions.storeMerkleRoot(
            str(issuance_batch.graduation_batch.name),  # Tên đợt (VD: "Dot_1_2026")
            str(issuance_batch.merkle_root)             # Mã băm
        ).build_transaction({
            'chainId': int(settings.CHAIN_ID),
            'gas': 2000000,
            'nonce': self.w3.eth.get_transaction_count(wallet_address),
        })

        # 2. Ký giao dịch bằng Private Key
        signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=settings.ISSUER_PRIVATE_KEY)

        # 3. Gửi lên Blockchain
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        # 4. Lưu lại lịch sử giao dịch vào Database của Django
        tx_hash_hex = self.w3.to_hex(tx_hash)
        BlockchainTransaction.objects.create(
            issuance_batch=issuance_batch,
            operation_type='ISSUE',
            tx_hash=tx_hash_hex,
            status='pending'
        )
        
        return tx_hash_hex