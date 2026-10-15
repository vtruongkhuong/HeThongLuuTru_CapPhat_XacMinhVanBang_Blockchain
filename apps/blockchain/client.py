import json
from pathlib import Path
from web3 import Web3
from django.conf import settings
from .models import BlockchainTransaction

DEFAULT_CONTRACT_ADDRESS = "0x8E53683464fE95222b854b9336ba1b8B6B913577"
DEFAULT_PROVIDER_URL = "https://rpc.sepolia.org"


class BlockchainClient:
    def __init__(self):
        provider_url = getattr(settings, 'WEB3_PROVIDER_URL', '') or DEFAULT_PROVIDER_URL
        contract_addr = getattr(settings, 'CONTRACT_ADDRESS', '') or DEFAULT_CONTRACT_ADDRESS

        # 1. Kết nối tới mạng Sepolia
        self.w3 = Web3(Web3.HTTPProvider(provider_url))

        # 2. Đọc file ABI an toàn bằng đường dẫn tuyệt đối
        abi_path = Path(settings.BASE_DIR) / 'apps' / 'blockchain' / 'contracts_abi' / 'DegreeVerification.json'
        with open(abi_path, encoding='utf-8') as f:
            abi = json.load(f)

        # 3. Khởi tạo Contract với checksum address
        self.contract_address = self.w3.to_checksum_address(contract_addr)
        self.contract = self.w3.eth.contract(address=self.contract_address, abi=abi)

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
            'chainId': int(getattr(settings, 'CHAIN_ID', 11155111) or 11155111),
            'gas': 2000000,
            'nonce': self.w3.eth.get_transaction_count(wallet_address),
        })

        signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=settings.ISSUER_PRIVATE_KEY)
        raw_tx = getattr(signed_tx, 'rawTransaction', None) or getattr(signed_tx, 'raw_transaction', None)
        tx_hash = self.w3.eth.send_raw_transaction(raw_tx)

        tx_hash_hex = self.w3.to_hex(tx_hash)
        BlockchainTransaction.objects.create(
            issuance_batch=issuance_batch,
            operation_type='ISSUE',
            tx_hash=tx_hash_hex,
            status='pending'
        )
        return tx_hash_hex

    def build_revoke_tx_data(self, degree_identifier):
        """[N1] Tạo mã hex data cho giao dịch thu hồi trên MetaMask"""
        try:
            fn = self.contract.functions.revokeDegree(str(degree_identifier))
            return fn._encode_transaction_data()
        except Exception as e:
            print(f"Lỗi tạo TX Data: {e}")
            return "0x"

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