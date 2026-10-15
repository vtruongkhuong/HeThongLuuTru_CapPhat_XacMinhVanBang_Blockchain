import hashlib
import re
from urllib.parse import urlparse, parse_qs

import cv2
import fitz
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


def landing_view(request):
    return render(request, 'verification/landing.html')


def _verify_merkle_and_contract(degree):
    """
    Đối chiếu DegreeMerkleProof trong DB với Merkle Root và trạng thái trên Smart Contract.
    Trả về tuple: (is_verified_on_chain: bool, is_revoked_on_chain: bool, proof_info: dict)
    """
    proof_info = {
        'has_proof': False,
        'local_merkle_root': None,
        'chain_merkle_root': None,
        'root_matched': False,
    }
    is_revoked_on_chain = (degree.status == 'REVOKED')

    # 1. Tìm bản ghi DegreeMerkleProof & IssuanceBatch (nếu đã tạo từ K2)
    proof_obj = getattr(degree, 'merkle_proof', None)
    if not proof_obj:
        try:
            DegreeMerkleProof = apps.get_model('blockchain', 'DegreeMerkleProof')
            proof_obj = DegreeMerkleProof.objects.filter(degree=degree).first()
        except LookupError:
            try:
                DegreeMerkleProof = apps.get_model('degrees', 'DegreeMerkleProof')
                proof_obj = DegreeMerkleProof.objects.filter(degree=degree).first()
            except LookupError:
                proof_obj = None

    issuance_batch = getattr(degree, 'issuance_batch', None) or getattr(proof_obj, 'issuance_batch', None)
    if issuance_batch:
        proof_info['local_merkle_root'] = getattr(issuance_batch, 'merkle_root', None)

    if proof_obj:
        proof_info['has_proof'] = True

    # 2. Gọi Smart Contract để đối chiếu getMerkleRoot và verifyDegree
    try:
        client = BlockchainClient()
        if issuance_batch and getattr(issuance_batch, 'graduation_batch', None):
            batch_name = issuance_batch.graduation_batch.name
            chain_root = client.get_merkle_root(batch_name)
            proof_info['chain_merkle_root'] = chain_root
            if chain_root and proof_info['local_merkle_root']:
                proof_info['root_matched'] = (str(chain_root).strip() == str(proof_info['local_merkle_root']).strip())

        # Kiểm tra trạng thái thu hồi trực tiếp qua hàm verifyDegree (sau K1)
        public_id = getattr(degree, 'credential_public_id', None) or getattr(degree, 'degree_hash', None)
        if public_id:
            chain_status = client.verify_degree_on_chain(public_id)
            if chain_status is False or (isinstance(chain_status, (list, tuple)) and len(chain_status) > 1 and chain_status[1] is True):
                is_revoked_on_chain = True
    except Exception:
        pass

    # Hợp lệ trên chuỗi khi văn bằng đã ISSUED và (khớp Merkle Root trên chain hoặc đã có tx_hash/merkle_proof)
    is_verified = (
        degree.status in ['ISSUED', 'REVOKED'] and (
            proof_info['root_matched'] or
            proof_info['has_proof'] or
            bool(getattr(degree, 'tx_hash', None))
        )
    )
    return is_verified, is_revoked_on_chain, proof_info


HASH_RE = re.compile(r'\b[0-9a-fA-F]{64}\b')


def _decode_qr_from_image(detectors, img):
    """Thử giải mã QR trên ảnh với nhiều cách tiền xử lý."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Thêm viền trắng quanh ảnh: QR cần vùng yên tĩnh (quiet zone)
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
    return None


def _pixmap_to_bgr(pix):
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 1:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    if pix.n == 4:
        return cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)


def _read_pdf(file_bytes):
    """Trả về (chuỗi QR hoặc None, mã hash 64 ký tự trong chữ hoặc None)."""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception:
        return None, None

    detectors = [cv2.QRCodeDetector()]
    if hasattr(cv2, "QRCodeDetectorAruco"):          # OpenCV >= 4.8, đọc QR tốt hơn
        detectors.insert(0, cv2.QRCodeDetectorAruco())

    qr_text, text_hash = None, None
    try:
        for page in doc:
            if not text_hash:
                m = HASH_RE.search(page.get_text())
                if m:
                    text_hash = m.group(0).lower()
            if not qr_text:
                for dpi in (200, 300, 400):
                    img = _pixmap_to_bgr(page.get_pixmap(dpi=dpi))
                    qr_text = _decode_qr_from_image(detectors, img)
                    if qr_text:
                        break
    finally:
        doc.close()
    return qr_text, text_hash


def _extract_query_from_pdf(uploaded_file):
    """[D1] Đọc QR (hoặc mã hash in trong file) để tra cứu; kèm SHA-256 của file."""
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
    context = {
        'searched': False,
        'degree': None,
        'student': None,
        'is_verified_on_chain': False,
        'verification_state': None,  # 'VALID' | 'REVOKED' | 'NOT_FOUND'
        'proof_info': None,
    }

    # Nhận mã từ POST (form nhập / quét QR), file PDF upload, hoặc GET (?q= từ QR Dashboard)
    search_query = ''
    pdf_hash = None

    if request.method == 'POST':
        search_query = request.POST.get('search_query', '').strip()
        uploaded_pdf = request.FILES.get('pdf_file') or request.FILES.get('file')
        if uploaded_pdf and not search_query:
            search_query, pdf_hash = _extract_query_from_pdf(uploaded_pdf)
    elif request.method == 'GET' and request.GET.get('q'):
        search_query = request.GET.get('q', '').strip()

    if not search_query and request.method != 'POST':
        return render(request, 'verification/public_search.html', context)

    if not search_query:
        messages.error(request, "Vui lòng nhập mã, quét QR hoặc tải file PDF để tra cứu.")
        return render(request, 'verification/public_search.html', context)

    # 1. KIỂM TRA GIỚI HẠN TẦN SUẤT (THROTTLING)
    is_allowed, retry_after = check_verification_throttle(request)
    if not is_allowed:
        messages.error(request, f"Bạn đã tra cứu quá nhanh. Vui lòng thử lại sau {retry_after} giây.")
        return render(request, 'verification/public_search.html', context)

    context['searched'] = True

    # 2. TRUY VẤN DATABASE (Tìm theo Mã văn bằng, Số hiệu, MSSV, CCCD hoặc Hash)
    lookup_q = (
        Q(student__student_code__iexact=search_query) |
        Q(student__national_id__iexact=search_query)
    )
    # Kiểm tra linh hoạt các trường định danh trên model Degree
    degree_field_names = [f.name for f in Degree._meta.get_fields()]
    for field_name in ['credential_public_id', 'serial_number', 'degree_code', 'degree_hash','canonical_hash', 'tx_hash', 'pdf_hash']:
        if field_name in degree_field_names:
            lookup_q |= Q(**{f"{field_name}__iexact": search_query})
            if pdf_hash:
                lookup_q |= Q(**{f"{field_name}__iexact": pdf_hash})

    degree = Degree.objects.select_related('student').filter(lookup_q).first()

    # 3. GHI LOG TRA CỨU (Mọi lượt tra cứu đều ghi VerificationLog)
    VerificationLog.objects.create(
        search_query=search_query[:255],
        degree=degree,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        is_successful=bool(degree and degree.status == 'ISSUED')
    )

    # 4. ĐỐI CHIẾU BLOCKCHAIN & TRẢ VỀ ĐÚNG 3 TRẠNG THÁI (HỢP LỆ / ĐÃ THU HỒI / KHÔNG TÌM THẤY)
    if degree:
        is_verified, is_revoked, proof_info = _verify_merkle_and_contract(degree)
        context['degree'] = degree
        context['student'] = degree.student
        context['is_verified_on_chain'] = is_verified
        context['proof_info'] = proof_info

        if is_revoked or degree.status == 'REVOKED':
            context['verification_state'] = 'REVOKED'
            messages.warning(request, "Cảnh báo: Văn bằng này ĐÃ BỊ THU HỒI!")
        elif degree.status == 'ISSUED':
            context['verification_state'] = 'VALID'
            messages.success(request, "Văn bằng HỢP LỆ và đã được xác thực toàn vẹn!")
        else:
            context['verification_state'] = 'NOT_FOUND'
            messages.error(request, "Văn bằng đang trong quá trình xử lý, chưa được phát hành chính thức.")
    else:
        context['verification_state'] = 'NOT_FOUND'
        messages.error(request, f"Không tìm thấy dữ liệu văn bằng cho mã: {search_query}")

    return render(request, 'verification/public_search.html', context)


def verify_temp_cert_view(request):
    """
    [N2] Trang tra cứu Giấy chứng nhận tốt nghiệp tạm thời (có logic thật)
    """
    context = {
        'searched': False,
        'student': None,
        'degree': None,
        'verification_state': None,
    }

    search_query = ''
    if request.method == 'POST':
        search_query = request.POST.get('search_query', '').strip()
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
        is_successful=bool(student)
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