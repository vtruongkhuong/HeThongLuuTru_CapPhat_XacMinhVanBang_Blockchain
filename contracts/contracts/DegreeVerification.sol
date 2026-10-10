// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DegreeVerification {
    address public owner;

    // Quản lý danh sách Cán bộ phát hành (Issuer)
    mapping(address => bool) public isIssuer;
    mapping(address => bool) public isPaused;

    // Lưu trữ Merkle Root theo tên đợt (batchName)
    mapping(string => string) private batchMerkleRoots;

    // Quản lý văn bằng bị thu hồi (Lưu mã hash của từng văn bằng cụ thể)
    mapping(string => bool) public revokedDegrees;

    // Các sự kiện (Event) để Backend có thể lắng nghe
    event MerkleRootStored(string batchName, string merkleRoot, uint256 timestamp);
    event IssuerAdded(address issuer);
    event IssuerRemoved(address issuer);
    event IssuerPaused(address issuer);
    event IssuerUnpaused(address issuer);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event DegreeRevoked(string degreeHash, uint256 timestamp);

    // Modifier: Chỉ Owner (Admin cao nhất) mới được thao tác
    modifier onlyOwner() {
        require(msg.sender == owner, "Loi: Chi Owner moi duoc thuc hien");
        _;
    }

    // Modifier: Chỉ những Issuer hợp lệ mới được cấp phát/thu hồi
    modifier onlyIssuer() {
        require(isIssuer[msg.sender], "Loi: Dia chi nay khong phai Issuer");
        require(!isPaused[msg.sender], "Loi: Issuer nay dang bi tam khoa");
        _;
    }

    // Khi deploy, người bấm nút sẽ mặc định là Owner và cũng là Issuer
    constructor() {
        owner = msg.sender;
        isIssuer[msg.sender] = true;
    }

    // --- 1. QUẢN LÝ QUYỀN (Chỉ Owner) ---
    function transferOwnership(address newOwner) public onlyOwner {
        require(newOwner != address(0), "Dia chi khong hop le");
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }

    function addIssuer(address issuer) public onlyOwner {
        isIssuer[issuer] = true;
        emit IssuerAdded(issuer);
    }

    function removeIssuer(address issuer) public onlyOwner {
        isIssuer[issuer] = false;
        emit IssuerRemoved(issuer);
    }

    function pauseIssuer(address issuer) public onlyOwner {
        isPaused[issuer] = true;
        emit IssuerPaused(issuer);
    }

    // --- 2. CẤP PHÁT VĂN BẰNG (Chỉ Issuer) ---
    function storeMerkleRoot(string memory _batchName, string memory _merkleRoot) public onlyIssuer {
        batchMerkleRoots[_batchName] = _merkleRoot;
        emit MerkleRootStored(_batchName, _merkleRoot, block.timestamp);
    }

    function getMerkleRoot(string memory _batchName) public view returns (string memory) {
        return batchMerkleRoots[_batchName];
    }

    // --- 3. THU HỒI VĂN BẰNG (Chỉ Issuer) ---
    function revokeDegree(string memory _degreeHash) public onlyIssuer {
        revokedDegrees[_degreeHash] = true;
        emit DegreeRevoked(_degreeHash, block.timestamp);
    }

    // Hàm Nghĩa sẽ gọi để kiểm tra xem bằng có bị thu hồi chưa
    function verifyDegreeRevoked(string memory _degreeHash) public view returns (bool) {
        return revokedDegrees[_degreeHash];
    }
}