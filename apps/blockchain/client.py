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

        account = self.w3.eth.account.from_key(settings.ISSUER_PRIVATE_KEY)
        wallet_address = account.address

        tx = self.contract.functions.storeMerkleRoot(
            str(issuance_batch.graduation_batch.name),
            str(issuance_batch.merkle_root)
        ).build_transaction({
            'chainId': int(settings.CHAIN_ID),
            'gas': 2000000,
            'nonce': self.w3.eth.get_transaction_count(wallet_address),
        })

        signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=settings.ISSUER_PRIVATE_KEY)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        tx_hash_hex = self.w3.to_hex(tx_hash)
        BlockchainTransaction.objects.create(
            issuance_batch=issuance_batch,
            operation_type='ISSUE',
            tx_hash=tx_hash_hex,
            status='pending'
        )
        return tx_hash_hex

    def get_merkle_root(self, batch_identifier):
        """[N2] Đọc Merkle Root của đợt cấp phát từ Smart Contract"""
        try:
            if not self.w3.is_connected():
                return None
            return self.contract.functions.getMerkleRoot(str(batch_identifier)).call()
        except Exception:
            return None

    def verify_degree_on_chain(self, degree_identifier):
        """[N2] Kiểm tra trạng thái hiệu lực/thu hồi của văn bằng trên Smart Contract (sau K1)"""
        try:
            if not self.w3.is_connected():
                return None
            if hasattr(self.contract.functions, 'verifyDegree'):
                return self.contract.functions.verifyDegree(str(degree_identifier)).call()
            return None
        except Exception:
            return None