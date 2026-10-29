import json
from pathlib import Path
from web3 import Web3
from django.conf import settings

DEFAULT_CONTRACT_ADDRESS = "0x8E53683464fE95222b854b9336ba1b8B6B913577"
DEFAULT_PROVIDER_URL = "https://ethereum-sepolia-rpc.publicnode.com"


class BlockchainClient:
    def __init__(self):
        provider_url = getattr(settings, 'WEB3_PROVIDER_URL', '') or DEFAULT_PROVIDER_URL
        contract_addr = getattr(settings, 'CONTRACT_ADDRESS', '') or DEFAULT_CONTRACT_ADDRESS

        # 1. Kết nối tới mạng Sepolia
        self.w3 = Web3(Web3.HTTPProvider(provider_url, request_kwargs={'timeout': 10}))

        # 2. Đọc file ABI an toàn bằng đường dẫn tuyệt đối
        abi_path = Path(settings.BASE_DIR) / 'apps' / 'blockchain' / 'contracts_abi' / 'DegreeVerification.json'
        with open(abi_path, encoding='utf-8') as f:
            abi = json.load(f)

        # 3. Khởi tạo Contract với checksum address
        self.contract_address = self.w3.to_checksum_address(contract_addr)
        self.contract = self.w3.eth.contract(address=self.contract_address, abi=abi)

    def build_issue_tx_data(self, batch_name: str, merkle_root_hex: str, count: int) -> str:
        """
        Tạo mã calldata cho hàm storeMerkleRoot(string batchName, bytes32 merkleRoot, uint32 count)
        để truyền ra giao diện cho MetaMask ký phát hành đợt.
        """
        clean_root = merkle_root_hex.replace('0x', '')
        root_bytes = bytes.fromhex(clean_root)
        
        # ĐÃ SỬA: Đổi storeBatch -> storeMerkleRoot cho khớp với Smart Contract ABI
        fn = self.contract.functions.storeMerkleRoot(str(batch_name), root_bytes, int(count))
        return fn._encode_transaction_data()

    def build_revoke_tx_data(self, batch_id_hex: str, leaf_hex: str, reason_code: int = 1) -> str:
        """
        Tạo mã calldata cho giao dịch thu hồi bằng MetaMask:
        revokeDegree(bytes32 batchId, bytes32 leaf, uint8 reason)
        """
        clean_batch_id = batch_id_hex.replace('0x', '')
        clean_leaf = leaf_hex.replace('0x', '')
        
        batch_id_bytes = bytes.fromhex(clean_batch_id)
        leaf_bytes = bytes.fromhex(clean_leaf)
        fn = self.contract.functions.revokeDegree(
            batch_id_bytes,
            leaf_bytes,
            int(reason_code)
        )
        return fn._encode_transaction_data()
    
    def batch_id_of(self, batch_name: str) -> str:
        """Tính mã batchId (bytes32 hex) từ tên đợt"""
        try:
            if not self.w3.is_connected():
                from eth_hash.auto import keccak
                return keccak(batch_name.encode('utf-8')).hex()
            b_id = self.contract.functions.batchIdOf(str(batch_name)).call()
            return b_id.hex()
        except Exception:
            from web3 import Web3
            return Web3.keccak(batch_name.encode('utf-8')).hex()

    def get_batch(self, batch_id_hex: str):
        """Đọc thông tin đợt cấp phát từ Smart Contract theo batchId"""
        try:
            if not self.w3.is_connected():
                return None
            clean_id = batch_id_hex.replace('0x', '')
            res = self.contract.functions.getBatch(bytes.fromhex(clean_id)).call()
            return {
                'root': res[0].hex(),
                'issued_at': res[1],
                'count': res[2],
                'issuer': res[3]
            }
        except Exception:
            return None

    def verify_degree_on_chain(self, batch_id_hex: str, leaf_hex: str, proof_hex_list: list) -> tuple:
        """
        Xác minh tính hợp lệ của văn bằng on-chain:
        verifyDegree(bytes32 batchId, bytes32 leaf, bytes32[] proof) -> (bool inBatch, bool revoked)
        """
        try:
            if not self.w3.is_connected():
                return False, False
            clean_batch_id = batch_id_hex.replace('0x', '')
            clean_leaf = leaf_hex.replace('0x', '')
            proof_bytes = [bytes.fromhex(p.replace('0x', '')) for p in proof_hex_list]
            in_batch, revoked = self.contract.functions.verifyDegree(
                bytes.fromhex(clean_batch_id),
                bytes.fromhex(clean_leaf),
                proof_bytes
            ).call()
            return in_batch, revoked
        except Exception:
            return False, False

    def is_degree_revoked(self, leaf_hex: str) -> bool:
        """Kiểm tra nhanh văn bằng đã bị thu hồi on-chain chưa"""
        try:
            if not self.w3.is_connected():
                return False
            clean_leaf = leaf_hex.replace('0x', '')
            leaf_bytes = bytes.fromhex(clean_leaf)
            # ĐÃ SỬA: Đổi isRevoked -> verifyDegreeRevoked cho khớp với Smart Contract ABI
            return self.contract.functions.verifyDegreeRevoked(leaf_bytes).call()
        except Exception:
            return False