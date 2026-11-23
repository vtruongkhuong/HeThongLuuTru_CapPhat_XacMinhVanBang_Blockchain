import os
import io
import datetime
import logging
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)


def get_or_create_signing_cert():
    """
    Tự động kiểm tra hoặc sinh cặp khóa RSA và chứng thư số X.509 tự ký (Self-Signed)
    chuẩn hóa phục vụ ký số PDF (pyHanko) cho Hệ thống Xác minh Blockchain.
    """
    certs_dir = Path(settings.BASE_DIR) / 'certs'
    certs_dir.mkdir(parents=True, exist_ok=True)

    key_path = certs_dir / 'digital_signature_key.pem'
    cert_path = certs_dir / 'digital_signature_cert.pem'

    if key_path.exists() and cert_path.exists():
        return str(key_path), str(cert_path)

    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        # 1. Sinh Private Key RSA 2048-bit
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )

        # 2. Xây dựng X.509 Certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "VN"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "HUTECH Blockchain Verification"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Digital Certificate Authority"),
            x509.NameAttribute(NameOID.COMMON_NAME, "HUTECH Digital Signing CA"),
        ])

        now = datetime.datetime.now(datetime.timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=3650))  # 10 năm
            .sign(private_key, hashes.SHA256())
        )

        # 3. Ghi file key.pem và cert.pem
        with open(key_path, 'wb') as f_k:
            f_k.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))

        with open(cert_path, 'wb') as f_c:
            f_c.write(cert.public_bytes(serialization.Encoding.PEM))

        logger.info(f"Đã khởi tạo cặp chứng thư số ký PDF tại: {cert_path}")
        return str(key_path), str(cert_path)

    except Exception as e:
        logger.error(f"Lỗi khi tạo chứng thư số tự ký: {e}", exc_info=True)
        return None, None


def sign_pdf_with_pyhanko(pdf_bytes: bytes, reason: str = "Xác nhận văn bằng điện tử nguyên bản trên Blockchain", location: str = "HUTECH Blockchain") -> bytes:
    """
    Ký số điện tử vào file PDF bằng thư viện pyHanko theo chuẩn PAdES / Adobe Digital Signature.
    Nếu có lỗi hoặc thiếu chứng thư, sẽ trả về file PDF gốc an toàn.
    """
    try:
        from pyhanko.sign import signers
        from pyhanko.pdf_utils.reader import PdfFileReader
        from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter

        key_path, cert_path = get_or_create_signing_cert()
        if not key_path or not cert_path:
            logger.warning("Không có chứng thư số, bỏ qua bước ký số pyHanko.")
            return pdf_bytes

        signer = signers.SimpleSigner.load(
            key_file=key_path,
            cert_file=cert_path,
        )

        input_stream = io.BytesIO(pdf_bytes)
        # Kiểm tra đọc được PDF
        _ = PdfFileReader(input_stream)
        input_stream.seek(0)

        writer = IncrementalPdfFileWriter(input_stream)
        output_stream = io.BytesIO()

        signers.sign_pdf(
            writer,
            signers.PdfSignatureMetadata(
                field_name='HUTECH_Digital_Signature',
                reason=reason,
                location=location
            ),
            signer=signer,
            output=output_stream
        )

        signed_bytes = output_stream.getvalue()
        if signed_bytes and len(signed_bytes) > len(pdf_bytes):
            logger.info("Ký số PDF bằng pyHanko thành công.")
            return signed_bytes

        return pdf_bytes

    except Exception as e:
        logger.warning(f"Không thể áp dụng chữ ký số pyHanko (sử dụng PDF gốc kèm dòng chứng thực trực quan): {e}")
        return pdf_bytes
