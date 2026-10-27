from django.test import SimpleTestCase
from apps.blockchain.services import (
    keccak256,
    generate_canonical_hash,
    build_merkle_tree,
    build_merkle_root,
    get_merkle_proof,
    verify_merkle_proof,
    _hash_pair
)
from apps.degrees.canonicalizer import canonical_hash, HASH_VERSION
from apps.blockchain.client import BlockchainClient
import uuid


class BlockchainCoreTests(SimpleTestCase):
    """Kiểm thử lõi Merkle Tree, Canonical Hash và sinh Calldata cho Khương."""

    def test_canonical_hash_consistency(self):
        """Đảm bảo hash JSON không phụ thuộc thứ tự key và là keccak256."""
        data_a = {"hash_version": "1", "student_code": "B2000001", "name": "Nguyen Van A"}
        data_b = {"name": "Nguyen Van A", "hash_version": "1", "student_code": "B2000001"}
        hash_a = canonical_hash(data_a)
        hash_b = canonical_hash(data_b)
        self.assertEqual(hash_a, hash_b)
        self.assertEqual(len(hash_a), 64)

    def test_merkle_tree_single_leaf(self):
        """Cây 1 lá thì root chính là lá đó."""
        leaf = canonical_hash({"id": 1})
        root, levels = build_merkle_tree([leaf])
        self.assertEqual(root, leaf)
        self.assertEqual(len(levels), 1)

    def test_merkle_proof_verification_multiple_leaves(self):
        """Tạo proof cho các lá và xác minh khớp root."""
        for num_leaves in [2, 3, 4, 7, 10]:
            leaves = [canonical_hash({"student_idx": i, "salt": str(uuid.uuid4())}) for i in range(num_leaves)]
            root = build_merkle_root(leaves)
            self.assertEqual(len(root), 64)

            for idx, leaf in enumerate(leaves):
                proof = get_merkle_proof(leaves, idx)
                is_valid = verify_merkle_proof(leaf, proof, root)
                self.assertTrue(is_valid, f"Proof không khớp tại lá #{idx} trên cây {num_leaves} lá")

    def test_blockchain_client_calldata_generation(self):
        """Kiểm tra sinh calldata cho MetaMask không cần private key."""
        client = BlockchainClient()
        batch_name = "DOT_TOT_NGHIEP_2026_TEST"
        dummy_root = "0x" + "a" * 64
        count = 15

        calldata = client.build_issue_tx_data(batch_name, dummy_root, count)
        self.assertTrue(calldata.startswith("0x"))
        # Hàm storeMerkleRoot(string,bytes32,uint32)
        self.assertGreater(len(calldata), 10)
