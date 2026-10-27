import hashlib
import re
import logging
from uuid import UUID
from urllib.parse import urlparse, parse_qs

import numpy as np
from django.shortcuts import render
from django.contrib import messages
from django.db.models import Q
from django.apps import apps

from apps.degrees.models import Degree
from apps.students.models import Student
from apps.blockchain.client import BlockchainClient
from .models import VerificationLog
from .throttling import check_verification_throttle, get_client_ip

logger = logging.getLogger(__name__)

# Thử import cv2 và fitz an toàn
try:
    import cv2
except ImportError:
    cv2 = None

try:
    import fitz
except ImportError:
    fitz = None

MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB
HASH_RE = re.compile(r'\b[0-9a-fA-F]{64}\b')


def landing_view(request):
    return render(request, 'verification/landing.html')


def _verify_merkle_and_contract(degree):
    """
    [N6] Đối chiếu DegreeMerkleProof trong DB với Merkle Root và gọi hàm Smart Contract
    verifyDegree(batchId, leaf, proof) -> (inBatch, revoked).
    Trả về: (is_valid_on_chain: bool, is_revoked_on_chain: bool, proof_info: dict, rpc_error: bool)
    """
    proof_info = {
        'has_proof': False,
        'local_merkle_root': None,
        'chain_merkle_root': None,
        'root_matched': False,
        'chain_batch_id': None,
    }
    is_revoked_on_chain = (degree.status == 'REVOKED')
    is_valid_on_chain = False
    rpc_error = False

    # 1. Tìm bản ghi DegreeMerkleProof & IssuanceBatch
    proof_obj = getattr(degree, 'merkle_proof', None)
    if not proof_obj:
        try:
            DegreeMerkleProof = apps.get_model('blockchain', 'DegreeMerkleProof')
            proof_obj = DegreeMerkleProof.objects.filter(degree=degree).first()
        except LookupError:
            proof_obj = None

    issuance_batch = getattr(degree, 'issuance_batch', None) or getattr(proof_obj, 'issuance_batch', None)
    if not issuance_batch and hasattr(degree, 'batch') and degree.batch:
        issuance_batch = degree.batch.issuance_batches.filter(status='CONFIRMED').first()

    if issuance_batch:
        proof_info['local_merkle_root'] = getattr(issuance_batch, 'merkle_root', None)
        proof_info['chain_batch_id'] = getattr(issuance_batch, 'chain_id', None)

    if proof_obj:
        proof_info['has_proof'] = True

    # 2. Gọi Smart Contract v2: verifyDegree(batchId, leaf, proof)
    try:
        client = BlockchainClient()
        if not client.w3.is_connected():
            return False, is_revoked_on_chain, proof_info, True

        batch_name = ""
        if issuance_batch and getattr(issuance_batch, 'graduation_batch', None):
            batch_name = issuance_batch.graduation_batch.name
        elif hasattr(degree, 'batch') and degree.batch:
            batch_name = degree.batch.name

        batch_id_hex = proof_info['chain_batch_id']
        if not batch_id_hex and batch_name:
            batch_id_hex = client.batch_id_of(batch_name)

        leaf_hex = getattr(proof_obj, 'leaf_hash', None) or degree.canonical_hash
        proof_list = getattr(proof_obj, 'proof_path', None) or []

        if batch_id_hex and leaf_hex:
            in_batch, revoked = client.verify_degree_on_chain(batch_id_hex, leaf_hex, proof_list)
            is_valid_on_chain = in_batch
            if revoked:
                is_revoked_on_chain = True

        # Đọc Merkle Root từ Smart Contract nếu có tên đợt
        if batch_name and hasattr(client.contract.functions, 'getMerkleRoot'):
            try:
                chain_root = client.contract.functions.getMerkleRoot(batch_name).call()
                chain_root_hex = chain_root.hex() if hasattr(chain_root, 'hex') else str(chain_root)
                proof_info['chain_merkle_root'] = chain_root_hex
                if chain_root_hex and proof_info['local_merkle_root']:
                    c_clean = chain_root_hex.replace('0x', '').lower()
                    l_clean = str(proof_info['local_merkle_root']).replace('0x', '').lower()
                    proof_info['root_matched'] = (c_clean == l_clean and len(c_clean) > 0 and c_clean != '0'*64)
            except Exception:
                pass

    except (ConnectionError, TimeoutError):
        return False, False, proof_info, True
    except Exception as e:
        logger.warning("Contract verifyDegree notice: %s", e)

    # Nếu trên DB trạng thái là ISSUED và đã có proof/tx_hash
    if not is_valid_on_chain and degree.status == 'ISSUED':
        is_valid_on_chain = bool(proof_info['root_matched'] or proof_info['has_proof'] or getattr(degree, 'tx_hash', None))

    return is_valid_on_chain, is_revoked_on_chain, proof_info, False


def _decode_qr_from_image(detectors, img):
    """Thử giải mã QR trên ảnh với OpenCV."""
    if cv2 is None or img is None:
        return None
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        padded = cv2.copyMakeBorder(gray, 80, 80, 80, 80, cv2.BORDER_CONSTANT, value=255)
        _, otsu = cv2.threshold(padded, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        big = cv2.resize(padded, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        variants = [padded, otsu, big, gray]

        for det in detectors:
            for v in variants:
                try:
                    data, _, _ = det.detectAndDecode(v)
                except Exception:
                    continue
                if data:
                    return data
    except Exception:
        pass
    return None


def _pixmap_to_bgr(pix):
    if cv2 is None:
        return None
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 1:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    if pix.n == 4:
        return cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)


def _read_pdf(file_bytes):
    """Trả về (chuỗi QR hoặc None, mã hash 64 ký tự trong chữ hoặc None)."""
    if fitz is None:
        return None, None

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception:
        return None, None

    detectors = []
    if cv2 is not None:
        if hasattr(cv2, "QRCodeDetectorAruco"):
            detectors.append(cv2.QRCodeDetectorAruco())
        detectors.append(cv2.QRCodeDetector())

    qr_text, text_hash = None, None
    try:
        for page in doc:
            if not text_hash:
                m = HASH_RE.search(page.get_text())
                if m:
                    text_hash = m.group(0).lower()
            if not qr_text and detectors:
                for dpi in (200, 300):
                    pix = page.get_pixmap(dpi=dpi)
                    img = _pixmap_to_bgr(pix)
                    qr_text = _decode_qr_from_image(detectors, img)
                    if qr_text:
                        break
    finally:
        doc.close()
    return qr_text, text_hash


def _extract_query_from_pdf(uploaded_file):
    """[N6] Trích xuất mã tra cứu từ file PDF (giới hạn 5MB)."""
    if uploaded_file.size > MAX_UPLOAD_SIZE:
        raise ValueError("File PDF tải lên vượt quá giới hạn 5 MB cho phép.")

    file_bytes = uploaded_file.read()
    uploaded_file.seek(0)
    pdf_sha256 = hashlib.sha256(file_bytes).hexdigest()

    qr_text, text_hash = _read_pdf(file_bytes)

    if qr_text:
        q = parse_qs(urlparse(qr_text).query).get('q')
        return (q[0] if q else qr_text.strip()), pdf_sha256
    if text_hash:
        return text_hash, pdf_sha256
    return pdf_sha256, pdf_sha256


def public_verify_view(request):
    """
    [N6] Cổng tra cứu xác minh công khai văn bằng:
    - Hỗ trợ quét QR webcam, kéo thả file PDF hoặc nhập mã định danh/UUID.
    - Gọi Smart Contract v2: verifyDegree(batchId, leaf, proof).
    - Trả về 3 trạng thái rõ ràng:
        1. HỢP LỆ (VALID)
        2. ĐÃ THU HỒI (REVOKED)
        3. KHÔNG TỒN TẠI (NOT_FOUND)
    - Giới hạn tải lên tối đa 5MB và ghi nhật ký tra cứu vào VerificationLog.
    """
    context = {
        'searched': False,
        'degree': None,
        'student': None,
        'is_verified_on_chain': False,
        'verification_state': None,  # 'VALID' | 'REVOKED' | 'NOT_FOUND' | 'UNVERIFIED'
        'proof_info': None,
        'error_detail': None,
    }

    # 1. KIỂM TRA THROTTLING
    is_allowed, retry_after = check_verification_throttle(request)
    if not is_allowed:
        messages.error(request, f"Bạn đã tra cứu quá nhanh. Vui lòng thử lại sau {retry_after} giây.")
        context['verification_state'] = 'RATE_LIMITED'
        return render(request, 'verification/public_search.html', context)

    search_query = ''
    uploaded_pdf_sha256 = None
    verification_type = 'CODE'

    if request.method == 'POST':
        search_query = request.POST.get('search_query', '').strip()
        uploaded_pdf = request.FILES.get('pdf_file') or request.FILES.get('file')

        if uploaded_pdf:
            verification_type = 'PDF'
            try:
                search_query, uploaded_pdf_sha256 = _extract_query_from_pdf(uploaded_pdf)
            except ValueError as ve:
                messages.error(request, str(ve))
                return render(request, 'verification/public_search.html', context)

    elif request.method == 'GET' and request.GET.get('q'):
        search_query = request.GET.get('q', '').strip()
        verification_type = 'QR' if request.GET.get('src') == 'qr' else 'CODE'

    if not search_query:
        if request.method == 'POST':
            messages.error(request, "Vui lòng nhập mã định danh văn bằng, quét QR hoặc tải file PDF để tra cứu.")
        return render(request, 'verification/public_search.html', context)

    context['searched'] = True

    # 2. TRUY VẤN CƠ SỞ DỮ LIỆU
    # Tra cứu bằng MÃ thay vì TÊN: UUID, Canonical Hash, MSSV, CCCD, Số hiệu (CTUT-...)
    lookup_q = Q(canonical_hash__iexact=search_query)

    try:
        val_uuid = UUID(search_query.strip())
        lookup_q |= Q(credential_public_id=val_uuid)
    except (ValueError, AttributeError):
        pass

    # Tra cứu theo Mã số sinh viên (MSSV) hoặc CCCD
    lookup_q |= Q(student__student_code__iexact=search_query)
    lookup_q |= Q(student__national_id__iexact=search_query)

    # Tra cứu theo số hiệu: CTUT-...-ID hoặc ID số
    m_serial = re.match(r'^CTUT-[^-]+-(\d+)$', search_query.strip(), re.IGNORECASE)
    if m_serial:
        try:
            lookup_q |= Q(pk=int(m_serial.group(1)))
        except (ValueError, TypeError):
            pass
    elif search_query.strip().isdigit():
        lookup_q |= Q(pk=int(search_query.strip()))

    degree = Degree.objects.select_related('student', 'degree_type', 'batch').filter(lookup_q).order_by('-id').first()

    # Nếu tìm qua SHA-256 của PDF tải lên
    if not degree and uploaded_pdf_sha256:
        degree = Degree.objects.filter(
            Q(canonical_hash__iexact=uploaded_pdf_sha256) | Q(pdf_path__icontains=uploaded_pdf_sha256)
        ).first()

    # 3. ĐỐI CHIẾU BLOCKCHAIN & TRẢ VỀ ĐÚNG 3 TRẠNG THÁI (VALID, REVOKED, NOT_FOUND)
    result_status = 'NOT_FOUND'

    if degree:
        is_valid_on_chain, is_revoked_on_chain, proof_info, rpc_error = _verify_merkle_and_contract(degree)
        context['degree'] = degree
        context['student'] = degree.student
        context['is_verified_on_chain'] = is_valid_on_chain
        context['proof_info'] = proof_info

        if rpc_error:
            context['verification_state'] = 'UNVERIFIED'
            result_status = 'UNVERIFIED'
            messages.warning(request, "Tạm thời không thể kết nối mạng Blockchain Sepolia. Dữ liệu văn bằng được hiển thị từ cơ sở dữ liệu nội bộ.")
        elif is_revoked_on_chain or degree.status == 'REVOKED':
            context['verification_state'] = 'REVOKED'
            result_status = 'REVOKED'
            messages.warning(request, "CẢNH BÁO: Văn bằng này ĐÃ BỊ THU HỒI trên hệ thống Blockchain và không còn hiệu lực!")
        elif degree.status == 'ISSUED':
            context['verification_state'] = 'VALID'
            result_status = 'VALID'
            messages.success(request, "VĂN BẰNG HỢP LỆ! Tính toàn vẹn và hợp thức đã được xác thực thành công trên Blockchain Sepolia.")
        else:
            context['verification_state'] = 'NOT_FOUND'
            result_status = 'NOT_FOUND'
            messages.error(request, "Văn bằng chưa được cấp phát chính thức lên mạng lưới.")
    else:
        context['verification_state'] = 'NOT_FOUND'
        result_status = 'NOT_FOUND'
        messages.error(request, f"Không tìm thấy văn bằng tương ứng với mã tra cứu: {search_query}")

    # 4. GHI NHẬN VERIFICATION LOG
    try:
        VerificationLog.objects.create(
            search_query=search_query[:255],
            degree=degree,
            verification_type=verification_type,
            result_status=result_status,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            is_successful=(result_status == 'VALID')
        )
    except Exception as e:
        logger.warning("Could not save VerificationLog: %s", e)

    return render(request, 'verification/public_search.html', context)


def verify_temp_cert_view(request):
    """Trang tra cứu Giấy chứng nhận tốt nghiệp tạm thời"""
    context = {
        'searched': False,
        'student': None,
        'degree': None,
        'verification_state': None,
    }

    search_query = ''
    if request.method == 'POST':
        search_query = request.POST.get('search_query', '').strip() or request.POST.get('verify_code', '').strip()
    elif request.method == 'GET' and request.GET.get('q'):
        search_query = request.GET.get('q', '').strip()

    if not search_query:
        if request.method == 'POST':
            messages.error(request, "Vui lòng nhập MSSV hoặc CCCD để tra cứu chứng nhận tạm thời.")
        return render(request, 'verification/verify_temp_cert.html', context)

    is_allowed, retry_after = check_verification_throttle(request)
    if not is_allowed:
        messages.error(request, f"Bạn thao tác quá nhanh. Vui lòng thử lại sau {retry_after} giây.")
        return render(request, 'verification/verify_temp_cert.html', context)

    context['searched'] = True
    student = Student.objects.filter(
        Q(student_code__iexact=search_query) | Q(national_id__iexact=search_query)
    ).first()
    degree = Degree.objects.filter(student=student).first() if student else None

    VerificationLog.objects.create(
        search_query=f"[TEMP_CERT] {search_query}"[:255],
        degree=degree,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        is_successful=bool(student),
        result_status='VALID' if bool(student) else 'INVALID',
        verification_type='TEMP_CERT'
    )

    if student:
        context['student'] = student
        context['degree'] = degree
        if degree and degree.status == 'REVOKED':
            context['verification_state'] = 'REVOKED'
            messages.warning(request, "Chứng nhận tốt nghiệp của sinh viên này đã bị thu hồi!")
        else:
            context['verification_state'] = 'VALID'
            messages.success(request, "Xác nhận sinh viên đủ điều kiện cấp Giấy chứng nhận tốt nghiệp tạm thời!")
    else:
        context['verification_state'] = 'NOT_FOUND'
        messages.error(request, f"Không tìm thấy hồ sơ tốt nghiệp tạm thời cho mã: {search_query}")

    return render(request, 'verification/verify_temp_cert.html', context)
