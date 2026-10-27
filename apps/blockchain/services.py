"""
Các hàm tính toán off-chain cho Blockchain:
  - keccak256               : băm Keccak-256 chuẩn Ethereum (có fallback thuần Python)
  - generate_canonical_hash : keccak256 canonical JSON
  - build_merkle_tree       : xây cây Merkle, trả (root, levels)
  - build_merkle_root       : chỉ lấy root
  - get_merkle_proof        : sinh proof path cho 1 lá
"""
import json


def _pure_python_keccak(data: bytes) -> bytes:
    """
    Thuật toán Keccak-256 (chuẩn Ethereum, padding 0x01 ... 0x80).
    Chạy thuần 100% Python, không cần cài bất kỳ thư viện C hay package ngoài nào.
    """
    RC = [
        0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
        0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
        0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
        0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
        0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
        0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008
    ]
    ROT = [
        [0, 36, 3, 41, 18],
        [1, 44, 10, 45, 2],
        [62, 6, 43, 15, 61],
        [28, 55, 25, 21, 56],
        [27, 20, 39, 8, 14]
    ]

    rate = 136  # 1088 bits = 136 bytes
    padded = bytearray(data)
    padded.append(0x01)
    while len(padded) % rate != (rate - 1):
        padded.append(0x00)
    padded.append(0x80)

    state = [[0] * 5 for _ in range(5)]

    for offset in range(0, len(padded), rate):
        block = padded[offset:offset + rate]
        for i in range(17):
            x = i % 5
            y = i // 5
            word = int.from_bytes(block[i * 8:(i + 1) * 8], 'little')
            state[x][y] ^= word

        for round_idx in range(24):
            # Theta
            C = [state[x][0] ^ state[x][1] ^ state[x][2] ^ state[x][3] ^ state[x][4] for x in range(5)]
            D = [C[(x - 1) % 5] ^ (((C[(x + 1) % 5] << 1) & 0xFFFFFFFFFFFFFFFF) | (C[(x + 1) % 5] >> 63)) for x in range(5)]
            for x in range(5):
                for y in range(5):
                    state[x][y] ^= D[x]

            # Rho & Pi
            B = [[0] * 5 for _ in range(5)]
            for x in range(5):
                for y in range(5):
                    r = ROT[x][y]
                    val = state[x][y]
                    B[y][(2 * x + 3 * y) % 5] = ((val << r) & 0xFFFFFFFFFFFFFFFF) | (val >> (64 - r) if r else 0)

            # Chi
            for x in range(5):
                for y in range(5):
                    state[x][y] = B[x][y] ^ ((~B[(x + 1) % 5][y]) & B[(x + 2) % 5][y])

            # Iota
            state[0][0] ^= RC[round_idx]

    out = bytearray()
    for y in range(5):
        for x in range(5):
            out.extend(state[x][y].to_bytes(8, 'little'))
            if len(out) >= 32:
                return bytes(out[:32])
    return bytes(out[:32])


def keccak256(data: bytes) -> bytes:
    """Hàm băm Keccak-256 trả về bytes (32 bytes). Tự động dùng eth_hash hoặc fallback."""
    try:
        from eth_hash.auto import keccak
        return keccak(data)
    except Exception:
        pass

    try:
        from Crypto.Hash import keccak
        k = keccak.new(digest_bits=256)
        k.update(data)
        return k.digest()
    except Exception:
        pass

    return _pure_python_keccak(data)


def generate_canonical_hash(degree_data: dict) -> str:
    """keccak256 của canonical JSON dict."""
    s = json.dumps(degree_data, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return keccak256(s.encode('utf-8')).hex()


def _hash_pair(left: str, right: str) -> str:
    """
    Ghép cặp hash theo thứ tự từ điển rồi keccak256.
    Đồng bộ với _verifyProof() trong Solidity (h < p ? h+p : p+h).
    """
    a, b = (left, right) if left <= right else (right, left)
    return keccak256(bytes.fromhex(a) + bytes.fromhex(b)).hex()


def build_merkle_tree(hash_list: list) -> tuple:
    """
    Xây cây Merkle đầy đủ từ danh sách leaf hash.
    Trả về: (root: str, levels: list[list[str]])
    """
    if not hash_list:
        return "", []

    levels = [list(hash_list)]

    while len(levels[-1]) > 1:
        current = levels[-1]
        next_level = []
        for i in range(0, len(current), 2):
            left = current[i]
            right = current[i + 1] if (i + 1) < len(current) else left
            next_level.append(_hash_pair(left, right))
        levels.append(next_level)

    return levels[-1][0], levels


def build_merkle_root(hash_list: list) -> str:
    """Chỉ lấy Merkle Root."""
    root, _ = build_merkle_tree(hash_list)
    return root


def get_merkle_proof(hash_list: list, index: int) -> list:
    """
    Sinh Merkle proof path cho lá tại vị trí `index`.
    Khớp 100% với hàm verifyDegree trong Smart Contract.
    """
    _, levels = build_merkle_tree(hash_list)
    proof = []
    idx = index

    for level in levels[:-1]:
        sibling_idx = idx ^ 1
        if sibling_idx < len(level):
            proof.append(level[sibling_idx])
        else:
            proof.append(level[idx])
        idx //= 2

    return proof


def verify_merkle_proof(leaf: str, proof: list, root: str) -> bool:
    """
    Xác minh Merkle proof off-chain.
    Logic ghép cặp sắp xếp theo thứ tự từ điển (h < p) khớp 100% với hàm verifyDegree() của Smart Contract.
    """
    if not leaf or not root:
        return False
    current = leaf.replace('0x', '').lower()
    target_root = root.replace('0x', '').lower()
    for p in proof:
        sibling = p.replace('0x', '').lower()
        current = _hash_pair(current, sibling)
    return current == target_root

