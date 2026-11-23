import hashlib
import json
from datetime import datetime, timezone as dt_timezone
from django.utils import timezone


ISSUER_DID = "did:web:ctut.edu.vn"
ISSUER_NAME = "Trường Đại học Kỹ thuật - Công nghệ Cần Thơ (CTUT)"
VC_CONTEXT = [
    "https://www.w3.org/2018/credentials/v1",
    "https://w3id.org/security/suites/ed25519-2020/v1",
]


def _iso_date(d) -> str:
    """Chuyển date/datetime sang chuỗi ISO 8601 UTC."""
    if d is None:
        return datetime.now(tz=dt_timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    if hasattr(d, 'strftime'):
        # date object
        return f"{d.strftime('%Y-%m-%d')}T00:00:00Z"
    return str(d)


def _make_proof(degree, vc_body: dict) -> dict:
    """
    Sinh proof CanonicalHash — dùng canonical_hash sẵn có trên Blockchain.
    Nếu chưa có tx_hash → proof type = CanonicalHashProof2024 (offline).
    """
    # Tính JCS-like fingerprint để làm proofValue
    body_bytes = json.dumps(vc_body, ensure_ascii=False, separators=(',', ':'), sort_keys=True).encode('utf-8')
    fingerprint = hashlib.sha256(body_bytes).hexdigest()

    tx_hash = None
    merkle_root = None
    try:
        from django.apps import apps
        DegreeMerkleProof = apps.get_model('blockchain', 'DegreeMerkleProof')
        proof_obj = DegreeMerkleProof.objects.filter(degree=degree).first()
        if proof_obj:
            issuance_batch = getattr(proof_obj, 'issuance_batch', None)
            if issuance_batch:
                tx_hash = getattr(issuance_batch, 'tx_hash', None)
                merkle_root = getattr(issuance_batch, 'merkle_root', None)
    except Exception:
        pass

    proof = {
        "type": "CanonicalHashProof2024",
        "created": _iso_date(timezone.now()),
        "verificationMethod": f"{ISSUER_DID}#keys-1",
        "proofPurpose": "assertionMethod",
        "canonicalHash": degree.canonical_hash,
        "proofValue": fingerprint,
    }
    if tx_hash:
        proof["ethereumTxHash"] = tx_hash
        proof["etherscanUrl"] = f"https://sepolia.etherscan.io/tx/{tx_hash}"
    if merkle_root:
        proof["merklRoot"] = merkle_root

    return proof


def generate_verifiable_credential(degree) -> dict:
    """
    Tạo W3C Verifiable Credential JSON cho một văn bằng.

    Args:
        degree: instance của apps.degrees.models.Degree

    Returns:
        dict — JSON-serializable W3C VC
    """
    student = degree.student
    major_name = student.major.name if (student and student.major) else ""
    degree_type_name = degree.degree_type.name if degree.degree_type else ""
    faculty_name = ""
    if student and hasattr(student, 'faculty') and student.faculty:
        faculty_name = student.faculty.name

    credential_id = f"https://ctut.edu.vn/credentials/{degree.credential_public_id}"

    issuance_date = _iso_date(degree.issue_date or degree.approved_at)
    expiration_date = None  # Văn bằng không hết hạn theo thông lệ VN

    vc_body = {
        "@context": VC_CONTEXT,
        "id": credential_id,
        "type": ["VerifiableCredential", "UniversityDegreeCredential"],
        "issuer": {
            "id": ISSUER_DID,
            "name": ISSUER_NAME,
            "url": "https://ctut.edu.vn",
        },
        "issuanceDate": issuance_date,
        "credentialSubject": {
            "id": f"did:example:{student.student_code}" if student else "did:example:unknown",
            "studentCode": student.student_code if student else "",
            "name": student.full_name if student else "",
            "dateOfBirth": _iso_date(getattr(student, 'date_of_birth', None)) if student else None,
            "degreeType": degree_type_name,
            "major": major_name,
            "faculty": faculty_name,
            "classification": degree.classification or "",
            "serialNumber": degree.serial_number,
            "degreeNumber": degree.serial_number,
            "issuanceDate": issuance_date,
            "status": degree.status,
            "isRevoked": degree.status == 'REVOKED',
        },
        "credentialStatus": {
            "id": f"https://ctut.edu.vn/api/v1/verify/{degree.credential_public_id}/",
            "type": "BlockchainRevocationList2024",
        },
    }

    if expiration_date:
        vc_body["expirationDate"] = expiration_date

    if degree.ipfs_cid:
        vc_body["evidence"] = [{
            "id": degree.ipfs_url or f"https://gateway.pinata.cloud/ipfs/{degree.ipfs_cid}",
            "type": ["DocumentVerification"],
            "verifier": ISSUER_DID,
            "evidenceDocument": "DegreePDF",
            "subjectPresence": "Digital",
            "documentPresence": "Digital",
            "ipfsCid": degree.ipfs_cid,
        }]

    # Proof phải được tính sau khi body hoàn chỉnh
    vc_body["proof"] = _make_proof(degree, vc_body)

    return vc_body
