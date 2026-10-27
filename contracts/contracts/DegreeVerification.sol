// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title DegreeVerification
/// @notice Bản tối ưu đa quyền (Multi-Admin) & tương thích ngược cao nhất:
///         - Hỗ trợ thêm Admin đồng cấp (Nghĩa có full quyền ký & quản trị như Owner)
///         - Hỗ trợ cả 2 cách gọi thu hồi: bản bytes32 tối ưu gas & bản string tương thích code cũ
///         - Cây Merkle bytes32 xác minh proof on-chain (N6)
contract DegreeVerification {
    // ------------------------------------------------------------------
    // Lỗi (Custom errors tiết kiệm gas)
    // ------------------------------------------------------------------
    error NotOwner();
    error NotAdmin();
    error NotPendingOwner();
    error NotIssuer();
    error IssuerIsPaused();
    error ZeroAddress();
    error EmptyRoot();
    error BatchExists();
    error BatchNotFound();
    error AlreadyRevoked();

    // ------------------------------------------------------------------
    // Cấu trúc dữ liệu (Đã tối ưu gói slot)
    // ------------------------------------------------------------------
    struct Batch {
        bytes32 root;      // slot 1
        uint64 issuedAt;   // slot 2: 8 + 4 + 20 = 32 bytes
        uint32 count;
        address issuer;
    }

    struct IssuerInfo {
        bool active;       // đang là Issuer
        bool paused;       // đang bị tạm khóa
    }

    struct Revocation {
        uint64 revokedAt;  // 0 = chưa thu hồi
        uint8 reason;      // 1: Sai thông tin, 2: Vi phạm kỷ luật, 3: Quyết định hủy bằng, 4: Khác
    }

    // ------------------------------------------------------------------
    // Trạng thái
    // ------------------------------------------------------------------
    address public owner;
    address public pendingOwner;

    mapping(address => bool) public admins;               // Danh sách Admin đồng cấp
    mapping(address => IssuerInfo) public issuers;        // Danh sách Issuer
    mapping(bytes32 => Batch) private _batches;           // batchId => Batch
    mapping(bytes32 => Revocation) private _revocations;  // leaf => Revocation

    // ------------------------------------------------------------------
    // Event
    // ------------------------------------------------------------------
    event MerkleRootStored(
        bytes32 indexed batchId,
        string batchName,
        bytes32 merkleRoot,
        uint32 count,
        address indexed issuer
    );
    event DegreeRevoked(bytes32 indexed leaf, bytes32 indexed batchId, uint8 reason);
    event AdminAdded(address indexed admin);
    event AdminRemoved(address indexed admin);
    event IssuerAdded(address indexed issuer);
    event IssuerRemoved(address indexed issuer);
    event IssuerPaused(address indexed issuer);
    event IssuerUnpaused(address indexed issuer);
    event OwnershipTransferStarted(address indexed previousOwner, address indexed newOwner);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    // ------------------------------------------------------------------
    // Modifier
    // ------------------------------------------------------------------
    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    modifier onlyAdmin() {
        if (msg.sender != owner && !admins[msg.sender]) revert NotAdmin();
        _;
    }

    modifier onlyIssuer() {
        // Owner và Admin luôn có quyền ký, không bao giờ bị chặn
        if (msg.sender != owner && !admins[msg.sender]) {
            IssuerInfo memory info = issuers[msg.sender];
            if (!info.active) revert NotIssuer();
            if (info.paused) revert IssuerIsPaused();
        }
        _;
    }

    /// @dev Người deploy contract vừa là Owner, vừa là Admin, vừa là Issuer
    constructor() {
        owner = msg.sender;
        admins[msg.sender] = true;
        issuers[msg.sender] = IssuerInfo({active: true, paused: false});
    }

    // ------------------------------------------------------------------
    // 1. Quản lý quyền Admin & Owner
    // ------------------------------------------------------------------

    /// Đề cử chủ sở hữu mới (2-step transfer an toàn)
    function transferOwnership(address newOwner) external onlyOwner {
        if (newOwner == address(0)) revert ZeroAddress();
        pendingOwner = newOwner;
        emit OwnershipTransferStarted(owner, newOwner);
    }

    /// Chủ sở hữu mới chấp nhận quyền
    function acceptOwnership() external {
        if (msg.sender != pendingOwner) revert NotPendingOwner();
        emit OwnershipTransferred(owner, msg.sender);
        owner = msg.sender;
        admins[msg.sender] = true;
        pendingOwner = address(0);
    }

    /// Thêm quyền Admin (Ví dụ: cấp quyền Admin cho Nghĩa để ký y hệt Owner)
    function addAdmin(address account) external onlyAdmin {
        if (account == address(0)) revert ZeroAddress();
        admins[account] = true;
        issuers[account] = IssuerInfo({active: true, paused: false});
        emit AdminAdded(account);
    }

    /// Thu hồi quyền Admin
    function removeAdmin(address account) external onlyAdmin {
        admins[account] = false;
        issuers[account] = IssuerInfo({active: false, paused: false});
        emit AdminRemoved(account);
    }

    function isAdmin(address account) external view returns (bool) {
        return account == owner || admins[account];
    }

    // ------------------------------------------------------------------
    // 2. Quản lý quyền Issuer (Owner hoặc Admin đều có quyền cấp/khóa)
    // ------------------------------------------------------------------

    function addIssuer(address issuer) external onlyAdmin {
        if (issuer == address(0)) revert ZeroAddress();
        issuers[issuer].active = true;
        emit IssuerAdded(issuer);
    }

    function removeIssuer(address issuer) external onlyAdmin {
        issuers[issuer] = IssuerInfo({active: false, paused: false});
        emit IssuerRemoved(issuer);
    }

    function pauseIssuer(address issuer) external onlyAdmin {
        if (!issuers[issuer].active) revert NotIssuer();
        issuers[issuer].paused = true;
        emit IssuerPaused(issuer);
    }

    function unpauseIssuer(address issuer) external onlyAdmin {
        if (!issuers[issuer].active) revert NotIssuer();
        issuers[issuer].paused = false;
        emit IssuerUnpaused(issuer);
    }

    function isIssuer(address account) external view returns (bool) {
        return account == owner || admins[account] || issuers[account].active;
    }

    function isPaused(address account) external view returns (bool) {
        if (account == owner || admins[account]) return false;
        return issuers[account].paused;
    }

    // ------------------------------------------------------------------
    // 3. Cấp phát (Issuer / Admin / Owner)
    // ------------------------------------------------------------------

    function storeMerkleRoot(
        string calldata batchName,
        bytes32 merkleRoot,
        uint32 count
    ) external onlyIssuer {
        if (merkleRoot == bytes32(0)) revert EmptyRoot();
        bytes32 batchId = keccak256(bytes(batchName));
        if (_batches[batchId].root != bytes32(0)) revert BatchExists();

        _batches[batchId] = Batch({
            root: merkleRoot,
            issuedAt: uint64(block.timestamp),
            count: count,
            issuer: msg.sender
        });

        emit MerkleRootStored(batchId, batchName, merkleRoot, count, msg.sender);
    }

    function getMerkleRoot(string calldata batchName) external view returns (bytes32) {
        return _batches[keccak256(bytes(batchName))].root;
    }

    // ------------------------------------------------------------------
    // 4. Thu hồi văn bằng (Hỗ trợ cả bản chuẩn bytes32 & bản string tương thích)
    // ------------------------------------------------------------------

    /// Bản chuẩn v2: Tối ưu gas với bytes32
    function revokeDegree(bytes32 batchId, bytes32 leaf, uint8 reason) public onlyIssuer {
        if (_batches[batchId].root == bytes32(0)) revert BatchNotFound();
        if (_revocations[leaf].revokedAt != 0) revert AlreadyRevoked();

        _revocations[leaf] = Revocation({revokedAt: uint64(block.timestamp), reason: reason});
        emit DegreeRevoked(leaf, batchId, reason);
    }

    /// Tương thích ngược: Cho phép truyền chuỗi string (mã hash hex hoặc public id)
    function revokeDegree(string calldata degreeHashOrId) external onlyIssuer {
        bytes32 leaf = _toBytes32(degreeHashOrId);
        if (_revocations[leaf].revokedAt != 0) revert AlreadyRevoked();

        _revocations[leaf] = Revocation({revokedAt: uint64(block.timestamp), reason: 1});
        emit DegreeRevoked(leaf, bytes32(0), 1);
    }

    /// Tương thích ngược: Cho phép truyền chuỗi string kèm lý do string
    function revokeDegree(string calldata degreeHashOrId, string calldata /* reason */) external onlyIssuer {
        bytes32 leaf = _toBytes32(degreeHashOrId);
        if (_revocations[leaf].revokedAt != 0) revert AlreadyRevoked();

        _revocations[leaf] = Revocation({revokedAt: uint64(block.timestamp), reason: 1});
        emit DegreeRevoked(leaf, bytes32(0), 1);
    }

    /// Kiểm tra trạng thái thu hồi bằng bytes32
    function verifyDegreeRevoked(bytes32 leaf) public view returns (bool) {
        return _revocations[leaf].revokedAt != 0;
    }

    /// Kiểm tra trạng thái thu hồi bằng string
    function verifyDegreeRevoked(string calldata degreeHashOrId) external view returns (bool) {
        bytes32 leaf = _toBytes32(degreeHashOrId);
        return _revocations[leaf].revokedAt != 0;
    }

    // ------------------------------------------------------------------
    // 5. Đọc & Xác minh Proof on-chain (Nghĩa - N6)
    // ------------------------------------------------------------------

    function batchIdOf(string calldata batchName) external pure returns (bytes32) {
        return keccak256(bytes(batchName));
    }

    function getBatch(bytes32 batchId)
        external
        view
        returns (bytes32 root, uint64 issuedAt, uint32 count, address issuer)
    {
        Batch memory b = _batches[batchId];
        return (b.root, b.issuedAt, b.count, b.issuer);
    }

    function getRevocation(bytes32 leaf) external view returns (uint64 revokedAt, uint8 reason) {
        Revocation memory r = _revocations[leaf];
        return (r.revokedAt, r.reason);
    }

    /// Xác minh trên chuỗi: leaf có thuộc đợt không và có bị thu hồi không.
    function verifyDegree(bytes32 batchId, bytes32 leaf, bytes32[] calldata proof)
        external
        view
        returns (bool inBatch, bool revoked)
    {
        bytes32 root = _batches[batchId].root;
        if (root == bytes32(0)) return (false, false);

        bytes32 h = leaf;
        for (uint256 i = 0; i < proof.length; ++i) {
            bytes32 p = proof[i];
            h = h < p ? keccak256(abi.encodePacked(h, p)) : keccak256(abi.encodePacked(p, h));
        }
        return (h == root, _revocations[leaf].revokedAt != 0);
    }

    // ------------------------------------------------------------------
    // Helper nội bộ: Chuyển đổi an toàn string (hex / uuid) sang bytes32
    // ------------------------------------------------------------------
    function _toBytes32(string calldata s) internal pure returns (bytes32 result) {
        bytes memory b = bytes(s);
        if (b.length == 66 && b[0] == "0" && (b[1] == "x" || b[1] == "X")) {
            uint256 val = 0;
            for (uint256 i = 2; i < 66; i++) {
                uint8 c = uint8(b[i]);
                uint8 nibble;
                if (c >= 48 && c <= 57) nibble = c - 48;
                else if (c >= 65 && c <= 70) nibble = c - 55;
                else if (c >= 97 && c <= 102) nibble = c - 87;
                else return keccak256(b);
                val = (val << 4) | nibble;
            }
            return bytes32(val);
        } else if (b.length == 64) {
            uint256 val = 0;
            for (uint256 i = 0; i < 64; i++) {
                uint8 c = uint8(b[i]);
                uint8 nibble;
                if (c >= 48 && c <= 57) nibble = c - 48;
                else if (c >= 65 && c <= 70) nibble = c - 55;
                else if (c >= 97 && c <= 102) nibble = c - 87;
                else return keccak256(b);
                val = (val << 4) | nibble;
            }
            return bytes32(val);
        }
        return keccak256(b);
    }
}
