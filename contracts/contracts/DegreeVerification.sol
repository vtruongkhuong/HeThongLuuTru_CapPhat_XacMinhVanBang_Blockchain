// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title DegreeVerification
/// @notice Giữ nguyên tên các hàm của bản cũ để backend và wallet.js ít phải sửa,
///         nhưng đã vá lỗi: root chỉ ghi một lần, có unpause, thu hồi gắn với đợt,
///         hash và root dùng bytes32 thay cho string.
contract DegreeVerification {
    // ------------------------------------------------------------------
    // Lỗi
    // ------------------------------------------------------------------
    error NotOwner();
    error NotPendingOwner();
    error NotIssuer();
    error IssuerIsPaused();
    error ZeroAddress();
    error EmptyRoot();
    error BatchExists();
    error BatchNotFound();
    error AlreadyRevoked();

    // ------------------------------------------------------------------
    // Cấu trúc dữ liệu
    // ------------------------------------------------------------------
    struct Batch {
        bytes32 root;      // slot 1
        uint64 issuedAt;   // slot 2: 8 + 4 + 20 = 32 byte
        uint32 count;
        address issuer;
    }

    struct IssuerInfo {
        bool active;       // đang là Issuer
        bool paused;       // đang bị tạm khóa
    }

    struct Revocation {
        uint64 revokedAt;  // 0 = chưa thu hồi
        uint8 reason;
    }

    // ------------------------------------------------------------------
    // Trạng thái
    // ------------------------------------------------------------------
    address public owner;
    address public pendingOwner;

    mapping(address => IssuerInfo) public issuers;
    mapping(bytes32 => Batch) private _batches;           // batchId => Batch
    mapping(bytes32 => Revocation) private _revocations;  // leaf => Revocation

    // ------------------------------------------------------------------
    // Event (giữ tên cũ; tham số của MerkleRootStored và DegreeRevoked đã đổi)
    // ------------------------------------------------------------------
    event MerkleRootStored(
        bytes32 indexed batchId,
        string batchName,
        bytes32 merkleRoot,
        uint32 count,
        address indexed issuer
    );
    event DegreeRevoked(bytes32 indexed leaf, bytes32 indexed batchId, uint8 reason);
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

    modifier onlyIssuer() {
        IssuerInfo memory info = issuers[msg.sender];
        if (!info.active) revert NotIssuer();
        if (info.paused) revert IssuerIsPaused();
        _;
    }

    /// @dev Giống bản cũ: ví deploy vừa là Owner vừa là Issuer (tiện test trên Remix).
    ///      Khi chạy thật nên gọi removeIssuer cho ví Owner và dùng ví backend riêng.
    constructor() {
        owner = msg.sender;
        issuers[msg.sender] = IssuerInfo({active: true, paused: false});
    }

    // ------------------------------------------------------------------
    // 1. Quản lý quyền (Owner) - tên hàm giống bản cũ
    // ------------------------------------------------------------------

    /// Bước 1: đề cử chủ mới (khác bản cũ: chưa chuyển ngay).
    function transferOwnership(address newOwner) external onlyOwner {
        if (newOwner == address(0)) revert ZeroAddress();
        pendingOwner = newOwner;
        emit OwnershipTransferStarted(owner, newOwner);
    }

    /// Bước 2: chủ mới gọi hàm này để nhận quyền.
    function acceptOwnership() external {
        if (msg.sender != pendingOwner) revert NotPendingOwner();
        emit OwnershipTransferred(owner, msg.sender);
        owner = msg.sender;
        pendingOwner = address(0);
    }

    function addIssuer(address issuer) external onlyOwner {
        if (issuer == address(0)) revert ZeroAddress();
        issuers[issuer].active = true;     // giữ nguyên cờ paused nếu có
        emit IssuerAdded(issuer);
    }

    function removeIssuer(address issuer) external onlyOwner {
        issuers[issuer] = IssuerInfo({active: false, paused: false}); // gỡ là xóa luôn khóa
        emit IssuerRemoved(issuer);
    }

    function pauseIssuer(address issuer) external onlyOwner {
        if (!issuers[issuer].active) revert NotIssuer();
        issuers[issuer].paused = true;
        emit IssuerPaused(issuer);
    }

    /// Mới
    function unpauseIssuer(address issuer) external onlyOwner {
        if (!issuers[issuer].active) revert NotIssuer();
        issuers[issuer].paused = false;
        emit IssuerUnpaused(issuer);
    }

    /// Giữ lại hai hàm đọc cũ (trước đây là mapping public).
    function isIssuer(address account) external view returns (bool) {
        return issuers[account].active;
    }

    function isPaused(address account) external view returns (bool) {
        return issuers[account].paused;
    }

    // ------------------------------------------------------------------
    // 2. Cấp phát (Issuer): root của một đợt chỉ ghi được một lần
    // ------------------------------------------------------------------

    /// Giữ tên cũ. Tham số đổi: root là bytes32 và thêm số lượng văn bằng.
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

    /// Giữ tên cũ. Trả bytes32 (rỗng = toàn số 0 nếu đợt chưa có).
    function getMerkleRoot(string calldata batchName) external view returns (bytes32) {
        return _batches[keccak256(bytes(batchName))].root;
    }

    // ------------------------------------------------------------------
    // 3. Thu hồi (Issuer)
    // ------------------------------------------------------------------

    /// Giữ tên cũ. Tham số đổi: thêm batchId (đợt phải tồn tại) và mã lý do.
    function revokeDegree(bytes32 batchId, bytes32 leaf, uint8 reason) external onlyIssuer {
        if (_batches[batchId].root == bytes32(0)) revert BatchNotFound();
        if (_revocations[leaf].revokedAt != 0) revert AlreadyRevoked();

        _revocations[leaf] = Revocation({revokedAt: uint64(block.timestamp), reason: reason});
        emit DegreeRevoked(leaf, batchId, reason);
    }

    /// Giữ tên cũ. Tham số đổi: hash văn bằng là bytes32.
    function verifyDegreeRevoked(bytes32 leaf) external view returns (bool) {
        return _revocations[leaf].revokedAt != 0;
    }

    // ------------------------------------------------------------------
    // 4. Đọc / xác minh
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
    /// Dùng keccak256, ghép cặp theo thứ tự sắp xếp (giống OpenZeppelin MerkleProof).
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
}
