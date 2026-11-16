// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title DegreeSoulboundToken (SBT - Non-transferable Diploma Token)
/// @notice Chuẩn văn bằng số NFT không thể chuyển nhượng (Soulbound Token - EIP-5114 / ERC-721 restricted)
///         - Bằng gắn liền vĩnh viễn với địa chỉ ví của sinh viên.
///         - Cấm tuyệt đối hành vi mua bán, chuyển nhượng (transferFrom / safeTransferFrom).
///         - Tích hợp liên kết siêu dữ liệu IPFS (tokenURI) và mã băm Canonical Hash.
contract DegreeSoulboundToken {
    // ------------------------------------------------------------------
    // Custom Errors
    // ------------------------------------------------------------------
    error SoulboundTokenCannotBeTransferred();
    error NotOwner();
    error NotIssuer();
    error ZeroAddress();
    error TokenAlreadyMinted();
    error TokenNotFound();
    error DegreeIsRevoked();

    // ------------------------------------------------------------------
    // Cấu trúc dữ liệu Văn bằng SBT
    // ------------------------------------------------------------------
    struct DegreeRecord {
        address student;
        string studentCode;
        bytes32 canonicalHash;
        string tokenURI;
        uint64 issuedAt;
        bool isRevoked;
        uint8 revokeReason;
    }

    string public name = "CTUT Degree Soulbound Token";
    string public symbol = "uSBT";

    address public owner;
    mapping(address => bool) public issuers;
    mapping(uint256 => DegreeRecord) private _degrees;
    mapping(address => uint256[]) private _studentTokens;
    uint256 public totalIssued;

    // ------------------------------------------------------------------
    // Sự kiện (Events)
    // ------------------------------------------------------------------
    event Transfer(address indexed from, address indexed to, uint256 indexed tokenId);
    event DegreeSBTMinted(address indexed student, uint256 indexed tokenId, bytes32 canonicalHash, string tokenURI);
    event DegreeSBTRevoked(uint256 indexed tokenId, uint8 reason);
    event IssuerStatusChanged(address indexed issuer, bool active);

    // ------------------------------------------------------------------
    // Modifiers
    // ------------------------------------------------------------------
    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    modifier onlyIssuer() {
        if (msg.sender != owner && !issuers[msg.sender]) revert NotIssuer();
        _;
    }

    constructor() {
        owner = msg.sender;
        issuers[msg.sender] = true;
    }

    // ------------------------------------------------------------------
    // Quản trị quyền Issuer
    // ------------------------------------------------------------------
    function setIssuer(address issuer, bool active) external onlyOwner {
        if (issuer == address(0)) revert ZeroAddress();
        issuers[issuer] = active;
        emit IssuerStatusChanged(issuer, active);
    }

    // ------------------------------------------------------------------
    // Phát hành SBT (Mint) vào ví sinh viên
    // ------------------------------------------------------------------
    function mintDegreeSBT(
        address student,
        uint256 tokenId,
        string calldata studentCode,
        bytes32 canonicalHash,
        string calldata ipfsTokenURI
    ) external onlyIssuer {
        if (student == address(0)) revert ZeroAddress();
        if (_degrees[tokenId].student != address(0)) revert TokenAlreadyMinted();

        _degrees[tokenId] = DegreeRecord({
            student: student,
            studentCode: studentCode,
            canonicalHash: canonicalHash,
            tokenURI: ipfsTokenURI,
            issuedAt: uint64(block.timestamp),
            isRevoked: false,
            revokeReason: 0
        });

        _studentTokens[student].push(tokenId);
        totalIssued++;

        // Chuẩn ERC-721: Phát Transfer từ 0x0 để các ví Web3 (MetaMask) nhận diện NFT
        emit Transfer(address(0), student, tokenId);
        emit DegreeSBTMinted(student, tokenId, canonicalHash, ipfsTokenURI);
    }

    // ------------------------------------------------------------------
    // Thu hồi văn bằng SBT
    // ------------------------------------------------------------------
    function revokeDegreeSBT(uint256 tokenId, uint8 reason) external onlyIssuer {
        DegreeRecord storage deg = _degrees[tokenId];
        if (deg.student == address(0)) revert TokenNotFound();
        if (deg.isRevoked) revert DegreeIsRevoked();

        deg.isRevoked = true;
        deg.revokeReason = reason;

        emit DegreeSBTRevoked(tokenId, reason);
    }

    // ------------------------------------------------------------------
    // Đọc thông tin (View)
    // ------------------------------------------------------------------
    function ownerOf(uint256 tokenId) external view returns (address) {
        address s = _degrees[tokenId].student;
        if (s == address(0)) revert TokenNotFound();
        return s;
    }

    function tokenURI(uint256 tokenId) external view returns (string memory) {
        if (_degrees[tokenId].student == address(0)) revert TokenNotFound();
        return _degrees[tokenId].tokenURI;
    }

    function getDegreeRecord(uint256 tokenId) external view returns (DegreeRecord memory) {
        if (_degrees[tokenId].student == address(0)) revert TokenNotFound();
        return _degrees[tokenId];
    }

    function getStudentTokens(address student) external view returns (uint256[] memory) {
        return _studentTokens[student];
    }

    // ------------------------------------------------------------------
    // KHÓA CỨNG: CẤM TUYỆT ĐỐI CHUYỂN NHƯỢNG (SOULBOUND PROPERTY)
    // ------------------------------------------------------------------
    function transferFrom(address /* from */, address /* to */, uint256 /* tokenId */) external pure {
        revert SoulboundTokenCannotBeTransferred();
    }

    function safeTransferFrom(address /* from */, address /* to */, uint256 /* tokenId */) external pure {
        revert SoulboundTokenCannotBeTransferred();
    }

    function safeTransferFrom(address /* from */, address /* to */, uint256 /* tokenId */, bytes calldata /* data */) external pure {
        revert SoulboundTokenCannotBeTransferred();
    }

    function approve(address /* to */, uint256 /* tokenId */) external pure {
        revert SoulboundTokenCannotBeTransferred();
    }

    function setApprovalForAll(address /* operator */, bool /* approved */) external pure {
        revert SoulboundTokenCannotBeTransferred();
    }

    function supportsInterface(bytes4 interfaceId) external pure returns (bool) {
        // Hỗ trợ ERC-165, ERC-721, ERC-721Metadata
        return interfaceId == 0x01ffc9a7 || interfaceId == 0x80ac58cd || interfaceId == 0x5b5e139f;
    }
}
