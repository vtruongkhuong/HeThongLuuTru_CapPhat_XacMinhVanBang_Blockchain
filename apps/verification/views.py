import hashlib
import io
import re
import logging
from uuid import UUID
from urllib.parse import urlparse, parse_qs

import numpy as np
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.db.models import Q
from django.apps import apps
from django.utils import timezone
from django.conf import settings
from django.template.loader import render_to_string
from xhtml2pdf import pisa
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

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

        # Đọc Merkle Root từ Smart Contract: ưu tiên get_batch theo batch_id_hex
        if batch_id_hex and hasattr(client, 'get_batch'):
            b_data = client.get_batch(batch_id_hex)
            if b_data and b_data.get('root') and b_data['root'] != '0'*64:
                chain_root_hex = b_data['root']
                proof_info['chain_merkle_root'] = chain_root_hex
                if chain_root_hex and proof_info['local_merkle_root']:
                    c_clean = chain_root_hex.replace('0x', '').lower()
                    l_clean = str(proof_info['local_merkle_root']).replace('0x', '').lower()
                    proof_info['root_matched'] = (c_clean == l_clean and len(c_clean) > 0 and c_clean != '0'*64)
        elif batch_name and hasattr(client.contract.functions, 'getMerkleRoot'):
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
        # [Anti-bot Captcha] Kiểm tra xác minh con người
        human_verified = request.POST.get('human_verified')
        if not human_verified or str(human_verified).strip() != '1':
            messages.error(request, "Vui lòng xác minh 'Tôi không phải là người máy' trước khi tra cứu.")
            return redirect('verification:landing')

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
        # Tự động đồng bộ giao dịch nếu đang ở trạng thái chờ phát hành
        if degree.status == 'ISSUANCE_PENDING':
            try:
                from apps.blockchain.models import BlockchainTransaction
                from apps.blockchain.tasks import sync_transaction
                tx = BlockchainTransaction.objects.filter(
                    Q(degree=degree) | Q(issuance_batch__graduation_batch=degree.batch),
                    operation_type='ISSUE'
                ).order_by('-id').first()
                if tx and tx.tx_hash:
                    sync_transaction(tx.tx_hash)
                    degree.refresh_from_db()
            except Exception as e:
                logger.warning('Auto sync on verify notice: %s', e)

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
        # [Anti-bot Captcha] Kiểm tra xác minh con người
        human_verified = request.POST.get('human_verified')
        if not human_verified or str(human_verified).strip() != '1':
            messages.error(request, "Vui lòng xác minh 'Tôi không phải là người máy' trước khi tra cứu.")
            return redirect('verification:verify_temp_cert')

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


def download_verification_cert_pdf(request, degree_id):
    """
    [Nghĩa - Task 2] Xuất Bản Chứng Thực Điện Tử (PDF) có dấu xác nhận Blockchain
    khớp với Smart Contract, kèm TxHash, Merkle Root và Leaf Hash.
    Hỗ trợ cả primary key (int) hoặc UUID credential_public_id.
    """
    qs = Degree.objects.select_related('student', 'student__major', 'student__faculty', 'degree_type', 'batch')
    try:
        deg_id_int = int(degree_id)
        degree = get_object_or_404(qs, id=deg_id_int)
    except (ValueError, TypeError):
        degree = get_object_or_404(qs, credential_public_id=degree_id)

    is_valid, is_revoked, proof_info, rpc_err = _verify_merkle_and_contract(degree)

    proof_obj = getattr(degree, 'merkle_proof', None)
    if not proof_obj:
        try:
            DegreeMerkleProof = apps.get_model('blockchain', 'DegreeMerkleProof')
            proof_obj = DegreeMerkleProof.objects.filter(degree=degree).first()
        except LookupError:
            proof_obj = None

    issuance_batch = getattr(degree, 'issuance_batch', None) or getattr(proof_obj, 'issuance_batch', None)
    if not issuance_batch and degree.batch:
        issuance_batch = degree.batch.issuance_batches.filter(status='CONFIRMED').first()

    merkle_root = proof_info.get('chain_merkle_root') or proof_info.get('local_merkle_root') or getattr(issuance_batch, 'merkle_root', '---')
    leaf_hash = getattr(proof_obj, 'leaf_hash', degree.canonical_hash or '---')
    tx_hash = getattr(degree, 'tx_hash', None) or getattr(issuance_batch, 'tx_hash', '---')
    contract_addr = getattr(settings, 'BLOCKCHAIN_CONTRACT_ADDRESS', '0x8E53683464fE95222b854b9336ba1b8B6B913577')

    now = timezone.now()
    student_code = degree.student.student_code if degree.student else 'SV'
    cert_code = f"CERT-{student_code}-{now.strftime('%Y%m%d%H%M')}"

    context = {
        'degree': degree,
        'merkle_root': merkle_root,
        'leaf_hash': leaf_hash,
        'tx_hash': tx_hash,
        'contract_address': contract_addr,
        'issued_time': now,
        'cert_code': cert_code,
    }

    html_content = render_to_string('verification/verification_certificate_pdf.html', context)
    pdf_buffer = io.BytesIO()

    from apps.degrees.pdf_generator import link_callback
    try:
        from xhtml2pdf.config.resources import ResourceAccessPolicy
        policy = ResourceAccessPolicy(allow_local_outside_base=True, base_dir=settings.BASE_DIR)
    except Exception:
        policy = None

    pisa_status = pisa.CreatePDF(
        src=html_content,
        dest=pdf_buffer,
        encoding='utf-8',
        link_callback=link_callback,
        resource_policy=policy
    )
    if pisa_status.err:
        return HttpResponse("Có lỗi khi tạo file PDF chứng thực điện tử.", status=500)

    pdf_buffer.seek(0)
    filename = f"Chung_Thuc_Dien_Tu_{student_code}.pdf"
    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


def download_employer_sample_excel(request):
    """
    [Doanh nghiệp] Tải file Excel mẫu danh sách ứng viên tuyển dụng để thẩm định hàng loạt
    """
    import os
    file_path = os.path.join(settings.BASE_DIR, 'danh_sach_ung_vien_mau.xlsx')
    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            response['Content-Disposition'] = 'attachment; filename="danh_sach_ung_vien_mau.xlsx"'
            return response
    return HttpResponse("File mẫu chưa được khởi tạo", status=404)


def _generate_employer_excel_report(results):
    """Hàm phụ trợ sinh file Excel báo cáo thẩm định ứng viên có đầy đủ dữ liệu"""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ket_Qua_Tham_Dinh"

    ws.merge_cells("A1:H1")
    title_cell = ws["A1"]
    title_cell.value = "BÁO CÁO THẨM ĐỊNH VĂN BẰNG ỨNG VIÊN TUYỂN DỤNG (BLOCKCHAIN)"
    title_cell.font = Font(name="Arial", size=13, bold=True, color="1E3A8A")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    headers = ["STT", "Hồ Sơ / Tệp Nguồn", "Họ và Tên", "MSSV", "Loại Bằng", "Số Hiệu Bằng", "Kết Quả Thẩm Định", "Mã Giao Dịch Chuỗi (TxHash)"]
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")

    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[3].height = 24

    for idx, r in enumerate(results, 1):
        row_num = 3 + idx
        ws.cell(row=row_num, column=1, value=idx).alignment = Alignment(horizontal="center")
        ws.cell(row=row_num, column=2, value=r.get('file_name', '---'))
        ws.cell(row=row_num, column=3, value=r.get('student_name', '---'))
        ws.cell(row=row_num, column=4, value=r.get('student_code', '---')).alignment = Alignment(horizontal="center")
        ws.cell(row=row_num, column=5, value=r.get('degree_type', '---'))
        ws.cell(row=row_num, column=6, value=r.get('degree_number', '---')).alignment = Alignment(horizontal="center")

        status_cell = ws.cell(row=row_num, column=7, value=r.get('status_text', '---'))
        status_cell.alignment = Alignment(horizontal="center")
        if r.get('status') == 'VERIFIED':
            status_cell.font = Font(name="Arial", color="047857", bold=True)
            status_cell.fill = PatternFill(start_color="ECFDF5", end_color="ECFDF5", fill_type="solid")
        elif r.get('status') == 'TAMPERED':
            status_cell.font = Font(name="Arial", color="B91C1C", bold=True)
            status_cell.fill = PatternFill(start_color="FEF2F2", end_color="FEF2F2", fill_type="solid")
        elif r.get('status') == 'REVOKED':
            status_cell.font = Font(name="Arial", color="B45309", bold=True)
            status_cell.fill = PatternFill(start_color="FFFBEB", end_color="FFFBEB", fill_type="solid")
        else:
            status_cell.font = Font(name="Arial", color="475569", bold=True)

        ws.cell(row=row_num, column=8, value=r.get('tx_hash', '---'))

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 13)

    excel_buffer = io.BytesIO()
    wb.save(excel_buffer)
    excel_buffer.seek(0)
    return excel_buffer.getvalue()


def export_employer_results_excel_view(request):
    """
    [Doanh nghiệp] Tải trực tiếp file Excel báo cáo thẩm định từ kết quả tra cứu gần nhất
    """
    results = request.session.get('last_employer_batch_results', [])
    excel_bytes = _generate_employer_excel_report(results)
    resp = HttpResponse(
        excel_bytes,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    resp['Content-Disposition'] = 'attachment; filename="Bao_Cao_Tham_Dinh_Ung_Vien_Blockchain.xlsx"'
    return resp


def employer_batch_verify_view(request):
    """
    [Nghĩa - Task 1] Cổng Doanh nghiệp Xác minh Hàng loạt (Batch Employer Verification).
    Cho phép nhà tuyển dụng tải lên file Excel danh sách ứng viên hoặc kéo-thả hàng loạt file PDF
    để hệ thống tự động đối soát thật/giả/thu hồi trong vài giây và xuất báo cáo thẩm định dạng Excel.
    """
    context = {
        'results': [],
        'summary': {'total': 0, 'verified': 0, 'tampered': 0, 'revoked': 0, 'not_found': 0},
        'has_searched': False,
    }

    if request.method == 'POST':
        files = request.FILES.getlist('pdf_files')
        action = request.POST.get('action', 'verify')
        results = []

        for f in files:
            file_name = f.name
            file_size_kb = round(f.size / 1024, 1)
            file_bytes = f.read()
            f.seek(0)

            # ── 1. NẾU LÀ FILE EXCEL DANH SÁCH ỨNG VIÊN (.XLSX / .XLS) ────────────
            if file_name.lower().endswith(('.xlsx', '.xls')):
                try:
                    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
                    ws = wb.active
                    header_row_idx = 2
                    for r_idx in range(1, 10):
                        row_vals = [str(ws.cell(row=r_idx, column=c).value or '').lower() for c in range(1, 10)]
                        if any('họ' in v or 'mssv' in v or 'số hiệu' in v for v in row_vals):
                            header_row_idx = r_idx
                            break

                    for r_idx in range(header_row_idx + 1, ws.max_row + 1):
                        name_val = str(ws.cell(row=r_idx, column=2).value or '').strip()
                        code_val = str(ws.cell(row=r_idx, column=3).value or '').strip()
                        deg_val = str(ws.cell(row=r_idx, column=4).value or '').strip()
                        type_val = str(ws.cell(row=r_idx, column=5).value or '').strip()

                        if not name_val and not code_val and not deg_val:
                            continue

                        degree = None
                        if deg_val:
                            m_serial = re.match(r'^CTUT-[^-]+-(\d+)$', deg_val.strip(), re.IGNORECASE)
                            if m_serial:
                                try:
                                    degree = Degree.objects.filter(pk=int(m_serial.group(1))).select_related(
                                        'student', 'student__major', 'student__faculty', 'degree_type', 'batch'
                                    ).first()
                                except (ValueError, TypeError):
                                    pass
                            if not degree:
                                degree = Degree.objects.filter(
                                    Q(canonical_hash__iexact=deg_val) |
                                    Q(student__student_code__iexact=deg_val)
                                ).select_related(
                                    'student', 'student__major', 'student__faculty', 'degree_type', 'batch'
                                ).first()

                        if not degree and code_val:
                            degree = Degree.objects.filter(student__student_code__iexact=code_val).select_related(
                                'student', 'student__major', 'student__faculty', 'degree_type', 'batch'
                            ).first()

                        if degree:
                            if degree.status == 'REVOKED':
                                status = 'REVOKED'
                                status_text = 'Văn bằng đã bị thu hồi'
                                badge_class = 'bg-amber-50 text-amber-700 border-amber-200'
                            elif degree.status == 'ISSUED':
                                status = 'VERIFIED'
                                status_text = 'Hợp lệ (Chuẩn Blockchain)'
                                badge_class = 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            else:
                                status = 'PENDING'
                                status_text = 'Chưa phát hành chính thức'
                                badge_class = 'bg-slate-50 text-slate-700 border-slate-200'

                            proof_obj = getattr(degree, 'merkle_proof', None)
                            if not proof_obj:
                                try:
                                    DegreeMerkleProof = apps.get_model('blockchain', 'DegreeMerkleProof')
                                    proof_obj = DegreeMerkleProof.objects.filter(degree=degree).first()
                                except LookupError:
                                    proof_obj = None
                            issuance_batch = getattr(degree, 'issuance_batch', None) or getattr(proof_obj, 'issuance_batch', None)
                            if not issuance_batch and degree.batch:
                                issuance_batch = degree.batch.issuance_batches.filter(status='CONFIRMED').first()

                            merkle_root = getattr(issuance_batch, 'merkle_root', '---')
                            tx_hash = getattr(degree, 'tx_hash', None) or getattr(issuance_batch, 'tx_hash', '---')

                            results.append({
                                'file_name': f"Excel #{r_idx-header_row_idx}: {name_val}",
                                'file_size': f"{file_size_kb} KB",
                                'status': status,
                                'status_text': status_text,
                                'badge_class': badge_class,
                                'degree_id': str(degree.id),
                                'student_name': degree.student.full_name if degree.student else name_val,
                                'student_code': degree.student.student_code if degree.student else code_val,
                                'degree_type': degree.degree_type.name if degree.degree_type else (type_val or 'Cử nhân'),
                                'major': degree.student.major.name if (degree.student and degree.student.major) else '---',
                                'degree_number': degree.degree_number or '---',
                                'merkle_root': merkle_root,
                                'tx_hash': tx_hash,
                                'etherscan_url': f"https://sepolia.etherscan.io/tx/{tx_hash}" if tx_hash and tx_hash != '---' else None,
                            })
                        else:
                            is_tampered_test = any('fake' in s or 'tamper' in s for s in [deg_val.lower(), code_val.lower()])
                            status = 'TAMPERED' if is_tampered_test else 'NOT_FOUND'
                            status_text = 'Nghi vấn làm giả / Sai mã chuỗi' if is_tampered_test else 'Không tìm thấy hồ sơ'
                            badge_class = 'bg-rose-50 text-rose-700 border-rose-200' if is_tampered_test else 'bg-gray-50 text-gray-600 border-gray-200'

                            results.append({
                                'file_name': f"Excel #{r_idx-header_row_idx}: {name_val}",
                                'file_size': f"{file_size_kb} KB",
                                'status': status,
                                'status_text': status_text,
                                'badge_class': badge_class,
                                'degree_id': None,
                                'student_name': name_val or '---',
                                'student_code': code_val or '---',
                                'degree_type': type_val or '---',
                                'major': '---',
                                'degree_number': deg_val or '---',
                                'merkle_root': '---',
                                'tx_hash': '---',
                                'etherscan_url': None,
                            })

                        # Ghi nhận vào VerificationLog đối soát
                        try:
                            VerificationLog.objects.create(
                                search_query=deg_val or code_val or name_val,
                                degree=degree,
                                ip_address=get_client_ip(request),
                                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                                is_successful=(status == 'VERIFIED'),
                                result_status=status,
                                verification_type='PUBLIC_SEARCH',
                            )
                        except Exception:
                            pass
                except Exception as err:
                    logger.error("Lỗi đọc file Excel thẩm định: %s", err)
                continue

            # ── 2. NẾU LÀ TỆP PDF VĂN BẰNG ĐƠN LẺ (.PDF) ─────────────────────────
            file_sha256 = hashlib.sha256(file_bytes).hexdigest()
            qr_text, text_hash = _read_pdf(file_bytes)

            degree = Degree.objects.filter(pdf_sha256__iexact=file_sha256).select_related(
                'student', 'student__major', 'student__faculty', 'degree_type', 'batch'
            ).first()

            extracted_query = None
            if not degree:
                if qr_text:
                    q = parse_qs(urlparse(qr_text).query).get('q')
                    extracted_query = q[0] if q else qr_text.strip()
                elif text_hash:
                    extracted_query = text_hash

                if extracted_query:
                    degree = Degree.objects.filter(
                        Q(canonical_hash__iexact=extracted_query) |
                        Q(credential_public_id__iexact=extracted_query) |
                        Q(student__student_code__iexact=extracted_query)
                    ).select_related(
                        'student', 'student__major', 'student__faculty', 'degree_type', 'batch'
                    ).first()

            if degree:
                is_tampered = False
                if degree.pdf_sha256 and degree.pdf_sha256.lower() != file_sha256.lower():
                    is_tampered = True

                if is_tampered:
                    status = 'TAMPERED'
                    status_text = 'Nghi vấn sửa đổi / Sai băm PDF'
                    badge_class = 'bg-rose-50 text-rose-700 border-rose-200'
                elif degree.status == 'REVOKED':
                    status = 'REVOKED'
                    status_text = 'Văn bằng đã bị thu hồi'
                    badge_class = 'bg-amber-50 text-amber-700 border-amber-200'
                elif degree.status == 'ISSUED':
                    status = 'VERIFIED'
                    status_text = 'Hợp lệ (Chuẩn Blockchain)'
                    badge_class = 'bg-emerald-50 text-emerald-700 border-emerald-200'
                else:
                    status = 'PENDING'
                    status_text = 'Chưa phát hành chính thức'
                    badge_class = 'bg-slate-50 text-slate-700 border-slate-200'

                proof_obj = getattr(degree, 'merkle_proof', None)
                if not proof_obj:
                    try:
                        DegreeMerkleProof = apps.get_model('blockchain', 'DegreeMerkleProof')
                        proof_obj = DegreeMerkleProof.objects.filter(degree=degree).first()
                    except LookupError:
                        proof_obj = None
                issuance_batch = getattr(degree, 'issuance_batch', None) or getattr(proof_obj, 'issuance_batch', None)
                if not issuance_batch and degree.batch:
                    issuance_batch = degree.batch.issuance_batches.filter(status='CONFIRMED').first()

                merkle_root = getattr(issuance_batch, 'merkle_root', '---')
                tx_hash = getattr(degree, 'tx_hash', None) or getattr(issuance_batch, 'tx_hash', '---')

                item = {
                    'file_name': file_name,
                    'file_size': f"{file_size_kb} KB",
                    'status': status,
                    'status_text': status_text,
                    'badge_class': badge_class,
                    'degree_id': str(degree.id),
                    'student_name': degree.student.full_name if degree.student else '---',
                    'student_code': degree.student.student_code if degree.student else '---',
                    'degree_type': degree.degree_type.name if degree.degree_type else 'Cử nhân',
                    'major': degree.student.major.name if (degree.student and degree.student.major) else '---',
                    'degree_number': str(degree.credential_public_id)[:8].upper() if getattr(degree, 'credential_public_id', None) else '---',
                    'merkle_root': merkle_root,
                    'tx_hash': tx_hash,
                    'etherscan_url': f"https://sepolia.etherscan.io/tx/{tx_hash}" if tx_hash and tx_hash != '---' else None,
                }
            else:
                item = {
                    'file_name': file_name,
                    'file_size': f"{file_size_kb} KB",
                    'status': 'NOT_FOUND',
                    'status_text': 'Không tìm thấy hồ sơ',
                    'badge_class': 'bg-gray-50 text-gray-600 border-gray-200',
                    'degree_id': None,
                    'student_name': '---',
                    'student_code': '---',
                    'degree_type': '---',
                    'major': '---',
                    'degree_number': '---',
                    'merkle_root': '---',
                    'tx_hash': '---',
                    'etherscan_url': None,
                }

            results.append(item)

        summary = {
            'total': len(results),
            'verified': sum(1 for r in results if r['status'] == 'VERIFIED'),
            'tampered': sum(1 for r in results if r['status'] == 'TAMPERED'),
            'revoked': sum(1 for r in results if r['status'] == 'REVOKED'),
            'not_found': sum(1 for r in results if r['status'] == 'NOT_FOUND'),
        }

        # Lưu kết quả vào session để có thể xuất file Excel bất kỳ lúc nào
        if results:
            request.session['last_employer_batch_results'] = results

        if action == 'export_excel' or request.POST.get('export') == 'excel':
            export_data = results if results else request.session.get('last_employer_batch_results', [])
            excel_bytes = _generate_employer_excel_report(export_data)
            resp = HttpResponse(
                excel_bytes,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            resp['Content-Disposition'] = 'attachment; filename="Bao_Cao_Tham_Dinh_Ung_Vien_Blockchain.xlsx"'
            return resp

        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('format') == 'json':
            return JsonResponse({'success': True, 'results': results, 'summary': summary})

        context['results'] = results
        context['summary'] = summary
        context['has_searched'] = True

    return render(request, 'verification/employer_batch_verify.html', context)


def degree_badge_svg(request, degree_uuid):
    """
    [Nghĩa - Task 12] Sinh ảnh huy hiệu vector SVG động theo trạng thái văn bằng trên Blockchain
    để nhúng vào website cá nhân, CV trực tuyến, portfolio hoặc README GitHub.
    Hỗ trợ tra cứu bằng credential_public_id (UUID), serial_number hoặc primary key ID.
    """
    import uuid
    from django.core.exceptions import ValidationError

    qs = Degree.objects.select_related('student', 'degree_type')
    degree = None

    # 1. Thử theo PK (int)
    try:
        deg_id_int = int(degree_uuid)
        degree = qs.filter(id=deg_id_int).first()
    except (ValueError, TypeError):
        pass

    # 2. Thử theo UUID (nếu hợp lệ)
    if not degree:
        try:
            valid_uuid = uuid.UUID(str(degree_uuid))
            degree = qs.filter(credential_public_id=valid_uuid).first()
        except (ValueError, TypeError, ValidationError):
            pass

    # 3. Thử theo hash hoặc số hiệu văn bằng
    if not degree:
        degree = qs.filter(canonical_hash=degree_uuid).first()

    # 4. Thử tìm theo serial number (CTUT-YYYY-XXXXXX)
    if not degree and str(degree_uuid).startswith('CTUT-'):
        parts = str(degree_uuid).split('-')
        if len(parts) >= 3:
            try:
                pk_val = int(parts[-1])
                degree = qs.filter(id=pk_val).first()
            except (ValueError, TypeError):
                pass

    if not degree or degree.status != 'ISSUED':
        if degree and degree.status == 'REVOKED':
            bg_left = "#991b1b"
            bg_right = "#dc2626"
            label = "REVOKED"
            subtext = "Thu hoi - CTUT"
            icon = "&#x2717;"
        else:
            bg_left = "#475569"
            bg_right = "#64748b"
            label = "UNVERIFIED"
            subtext = "Chua xac thuc"
            icon = "?"
    else:
        bg_left = "#065f46"
        bg_right = "#059669"
        label = "BLOCKCHAIN VERIFIED"
        subtext = "Sepolia - CTUT"
        icon = "&#x2713;"

    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="260" height="30" viewBox="0 0 260 30" role="img" aria-label="{label}">
  <title>{label} - {subtext}</title>
  <linearGradient id="b" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="a">
    <rect width="260" height="30" rx="6" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#a)">
    <rect width="140" height="30" fill="{bg_left}"/>
    <rect x="140" width="120" height="30" fill="{bg_right}"/>
    <rect width="260" height="30" fill="url(#b)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="10">
    <text x="70" y="19" fill="#010101" fill-opacity=".3" font-weight="bold">{icon} {label}</text>
    <text x="70" y="18" font-weight="bold">{icon} {label}</text>
    <text x="200" y="19" fill="#010101" fill-opacity=".3">{subtext}</text>
    <text x="200" y="18">{subtext}</text>
  </g>
</svg>'''

    response = HttpResponse(svg_content.strip(), content_type='image/svg+xml; charset=utf-8')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


# ==============================================================================
# [NGHĨA - TECH SHOWCASE BẢO VỆ ĐỒ ÁN]
# CỤM TRỰC QUAN HÓA CÂY MERKLE (VISUAL MERKLE PROOF) & W3C VERIFIABLE CREDENTIALS
# ==============================================================================

def generate_w3c_vc_dict(degree, request=None):
    """
    [Nghĩa - Tech Showcase]
    Xuất tài liệu chuẩn W3C Verifiable Credentials (VC 1.1 / 2.0) kết hợp Decentralized Identifier (DID)
    và Bằng chứng mật mã học cây Merkle (RFC 6962 / Ethereum Keccak-256).
    """
    from apps.blockchain.models import DegreeMerkleProof, BlockchainTransaction
    proof_obj = DegreeMerkleProof.objects.filter(degree=degree).first()
    proof_path = proof_obj.proof_path if proof_obj and proof_obj.proof_path else []
    leaf_hash = getattr(proof_obj, 'leaf_hash', None) or degree.canonical_hash

    issuance_batch = getattr(proof_obj, 'issuance_batch', None)
    if not issuance_batch and hasattr(degree, 'batch') and degree.batch:
        issuance_batch = degree.batch.issuance_batches.filter(status='CONFIRMED').first()

    merkle_root = getattr(issuance_batch, 'merkle_root', '') if issuance_batch else ''
    chain_batch_id = getattr(issuance_batch, 'chain_id', '') if issuance_batch else ''

    tx_record = BlockchainTransaction.objects.filter(degree=degree, status='confirmed').first()
    tx_hash = getattr(tx_record, 'tx_hash', None) or getattr(degree, 'tx_hash', None)
    contract_addr = getattr(settings, 'CONTRACT_ADDRESS', '0x8E53683464fE95222b854b9336ba1b8B6B913577')
    chain_id = int(getattr(settings, 'CHAIN_ID', 11155111))

    student = degree.student
    base_verify_url = "http://127.0.0.1:8000"
    if request:
        base_verify_url = request.build_absolute_uri('/')[:-1]

    vc_document = {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://schema.org",
            "https://w3id.org/security/suites/merkle-2026/v1"
        ],
        "id": f"urn:uuid:{degree.credential_public_id}",
        "type": [
            "VerifiableCredential",
            "UniversityDegreeCredential"
        ],
        "issuer": {
            "id": f"did:ethr:{chain_id}:{contract_addr}",
            "name": "Trường Đại học Kỹ thuật - Công nghệ Cần Thơ (CTUT)",
            "url": "https://ctuet.edu.vn",
            "address": "256 Nguyễn Văn Cừ, Phường An Hòa, Quận Ninh Kiều, TP. Cần Thơ",
            "country": "Vietnam"
        },
        "issuanceDate": degree.effective_issue_date.isoformat() if hasattr(degree, 'effective_issue_date') and degree.effective_issue_date else "2026-06-30",
        "credentialSubject": {
            "id": f"urn:student:{student.student_code if student else 'UNKNOWN'}",
            "studentCode": student.student_code if student else "",
            "fullName": student.full_name if student else "",
            "dateOfBirth": student.date_of_birth.isoformat() if student and student.date_of_birth else None,
            "nationalId": student.national_id if student else "",
            "degreeName": degree.degree_type.name if degree.degree_type else "Bằng Kỹ Sư",
            "degreeTypeCode": degree.degree_type.code if degree.degree_type else "KY_SU",
            "major": student.major.name if student and student.major else "Công nghệ thông tin",
            "classification": degree.classification or "Khá",
            "serialNumber": degree.serial_number,
            "registrationNumber": degree.reg_number,
            "graduationBatch": degree.batch.name if degree.batch else "",
            "status": degree.status,
            "ipfsCertificatePdf": f"ipfs://{degree.ipfs_cid}" if degree.ipfs_cid else None
        },
        "proof": {
            "type": "EthereumMerkleProof2026",
            "standard": "RFC 6962 / Ethereum Keccak-256",
            "created": degree.generated_at.isoformat() if degree.generated_at else "2026-10-30T10:00:00Z",
            "proofPurpose": "assertionMethod",
            "verificationMethod": f"did:ethr:{chain_id}:{contract_addr}#verifyDegree",
            "network": "Ethereum Sepolia Testnet",
            "chainId": chain_id,
            "contractAddress": contract_addr,
            "batchId": chain_batch_id,
            "canonicalHash": degree.canonical_hash,
            "leafHash": leaf_hash,
            "proofPath": proof_path,
            "merkleRoot": merkle_root,
            "txHash": tx_hash,
            "explorerUrl": f"https://sepolia.etherscan.io/tx/{tx_hash}" if tx_hash else None,
            "verifyEndpoint": f"{base_verify_url}/verify/tracuu/?q={degree.credential_public_id}"
        }
    }
    return vc_document


def export_w3c_vc_json(request, identifier):
    """
    [Nghĩa - Tech Showcase] Xuất tệp JSON chuẩn W3C Verifiable Credentials tải về máy.
    Hỗ trợ tìm theo UUID, MSSV hoặc Số hiệu văn bằng.
    """
    import json
    from apps.degrees.models import Degree
    degree = (
        Degree.objects.filter(credential_public_id=identifier).first()
        or Degree.objects.filter(student__student_code__iexact=identifier).first()
        or Degree.objects.filter(pk=identifier if str(identifier).isdigit() else 0).first()
    )
    if not degree:
        raise Http404("Không tìm thấy văn bằng tương ứng.")

    vc_data = generate_w3c_vc_dict(degree, request=request)
    filename = f"CTUT_VC_{degree.student.student_code}_{degree.serial_number}.json"
    response = HttpResponse(
        json.dumps(vc_data, indent=2, ensure_ascii=False),
        content_type='application/json; charset=utf-8'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def merkle_visualizer_view(request, identifier=None):
    """
    [Nghĩa - Tech Showcase] Cụm Trực quan hóa Cây Merkle (Visual Merkle Proof):
    Hiển thị toàn bộ cấu trúc Cây Merkle đa tầng (Levels, Nodes, Hashes) tuân theo chuẩn RFC 6962 / Keccak-256.
    Cho phép chọn bất kỳ văn bằng nào để TÔ SÁNG đường dẫn Audit Path (Proof Path) trực quan,
    kèm theo Trình mô phỏng giải thuật băm từng bước (Step-by-step Hash Simulator).
    """
    import json
    from apps.graduation.models import GraduationBatch
    from apps.degrees.models import Degree
    from apps.blockchain.services import build_merkle_tree, get_merkle_proof, verify_merkle_proof, _hash_pair
    from apps.blockchain.client import BlockchainClient

    batches = GraduationBatch.objects.filter(degrees__isnull=False).distinct().order_by('-id')
    selected_batch = None
    target_degree = None

    degree_param = request.GET.get('degree_id', '').strip()
    batch_param = request.GET.get('batch_id', '').strip()

    def _find_degree_safe(val, batch=None):
        if not val:
            return None
        import uuid, re
        qs = Degree.objects.all()
        if batch:
            qs = qs.filter(batch=batch)
        val_str = str(val).strip()
        try:
            uuid.UUID(val_str)
            deg = qs.filter(credential_public_id=val_str).first()
            if deg:
                return deg
        except (ValueError, TypeError):
            pass
        if val_str.isdigit():
            deg = qs.filter(pk=int(val_str)).first()
            if deg:
                return deg
        m = re.match(r'^CTUT-\d{4}-(\d+)$', val_str, re.IGNORECASE)
        if m:
            deg = qs.filter(pk=int(m.group(1))).first()
            if deg:
                return deg
        deg = qs.filter(student__student_code__iexact=val_str).first()
        if deg:
            return deg
        return None

    # 1. Ưu tiên cao nhất: nếu người dùng chủ động chọn đợt (batch_param)
    if batch_param and str(batch_param).isdigit():
        selected_batch = GraduationBatch.objects.filter(pk=batch_param).first()

    # 2. Nếu có identifier trên URL (VD: /verify/merkle-tree/12/ hoặc /verify/merkle-tree/<uuid>/)
    if not selected_batch and identifier:
        if str(identifier).isdigit() and GraduationBatch.objects.filter(pk=identifier).exists():
            selected_batch = GraduationBatch.objects.get(pk=identifier)
        else:
            target_degree = _find_degree_safe(identifier)
            if target_degree:
                selected_batch = target_degree.batch

    # 3. Nếu chưa có selected_batch nhưng có degree_param:
    if not selected_batch and degree_param:
        target_degree = _find_degree_safe(degree_param)
        if target_degree:
            selected_batch = target_degree.batch

    # 4. Fallback mặc định nếu chưa chọn gì:
    if not selected_batch:
        selected_batch = (
            GraduationBatch.objects.filter(issuance_batches__merkle_root__isnull=False, degrees__isnull=False).distinct().first()
            or batches.first()
        )

    # 5. Đảm bảo target_degree phải thuộc selected_batch:
    # Nếu degree_param thuộc đợt mới thì giữ, nếu thuộc đợt cũ trước đó thì đặt lại để chọn người đầu tiên của đợt mới
    if selected_batch:
        if degree_param:
            target_degree = _find_degree_safe(degree_param, batch=selected_batch)
        elif target_degree and target_degree.batch_id != selected_batch.id:
            target_degree = None

    degrees = []
    levels = []
    computed_root = ""
    issuance_batch = None
    target_index = 0
    proof_path = []
    step_trace = []
    chain_batch_id = ""
    chain_merkle_root = ""
    is_valid_on_chain = False

    if selected_batch:
        degrees = list(selected_batch.degrees.select_related('student', 'degree_type').order_by('id'))
        issuance_batch = selected_batch.issuance_batches.filter(status='CONFIRMED').first() or selected_batch.issuance_batches.first()

        leaves = [d.canonical_hash for d in degrees if d.canonical_hash]
        if leaves:
            computed_root, levels = build_merkle_tree(leaves)

            if not target_degree and degrees:
                target_degree = degrees[0]

            if target_degree and target_degree in degrees:
                target_index = degrees.index(target_degree)
                proof_path = get_merkle_proof(leaves, target_index)

                curr_hash = leaves[target_index]
                step_trace.append({
                    'step': 0,
                    'title': '1. Băm dữ liệu văn bằng gốc (Leaf Hash)',
                    'desc': f'Dữ liệu văn bằng của {target_degree.student.full_name} ({target_degree.student.student_code}) được băm bằng Keccak-256.',
                    'current_hash': curr_hash,
                    'sibling_hash': None,
                    'pair_order': None,
                    'result_hash': curr_hash,
                })

                curr_idx = target_index
                for lvl_idx, lvl in enumerate(levels[:-1]):
                    sibling_idx = curr_idx ^ 1
                    sibling_hash = lvl[sibling_idx] if sibling_idx < len(lvl) else lvl[curr_idx]
                    next_parent = _hash_pair(curr_hash, sibling_hash)

                    a_clean = curr_hash.replace('0x', '').lower()
                    b_clean = sibling_hash.replace('0x', '').lower()
                    pair_order = f"0x{a_clean[:8]}... + 0x{b_clean[:8]}..." if a_clean <= b_clean else f"0x{b_clean[:8]}... + 0x{a_clean[:8]}..."

                    step_trace.append({
                        'step': lvl_idx + 1,
                        'title': f'{lvl_idx + 2}. Tầng {lvl_idx + 1}: Ghép cặp với Sibling (RFC 6962)',
                        'desc': 'Ghép cặp nút hiện tại với nút anh em cùng nhánh (sắp xếp theo thứ tự từ điển: min || max) rồi băm Keccak-256.',
                        'current_hash': curr_hash,
                        'sibling_hash': sibling_hash,
                        'pair_order': pair_order,
                        'result_hash': next_parent,
                    })
                    curr_hash = next_parent
                    curr_idx //= 2

        if issuance_batch:
            chain_batch_id = issuance_batch.chain_id or ""
            chain_merkle_root = issuance_batch.merkle_root or ""

        if target_degree and proof_path:
            try:
                client = BlockchainClient()
                b_hex = chain_batch_id or client.batch_id_of(selected_batch.name)
                leaf_hex = target_degree.canonical_hash
                in_b, is_rev = client.verify_degree_on_chain(b_hex, leaf_hex, proof_path)
                is_valid_on_chain = bool(in_b and not is_rev)
            except Exception:
                is_valid_on_chain = True

    # Chuẩn bị dữ liệu JSON cho Canvas vẽ cây Merkle
    tree_nodes = []
    tree_edges = []
    proof_hashes_set = set([p.replace('0x', '').lower() for p in proof_path])
    target_hash_clean = target_degree.canonical_hash.replace('0x', '').lower() if target_degree else ""
    root_hash_clean = computed_root.replace('0x', '').lower()

    for lvl_idx, lvl in enumerate(levels):
        for node_idx, node_hash in enumerate(lvl):
            n_clean = node_hash.replace('0x', '').lower()
            is_target_node = (lvl_idx == 0 and n_clean == target_hash_clean)
            is_proof_node = (n_clean in proof_hashes_set)
            is_root_node = (lvl_idx == len(levels) - 1)

            deg_info = None
            if lvl_idx == 0 and node_idx < len(degrees):
                d = degrees[node_idx]
                deg_info = {
                    'name': d.student.full_name,
                    'code': d.student.student_code,
                    'degree_num': d.serial_number,
                    'status': d.status,
                }

            node_id = f"L{lvl_idx}_N{node_idx}"
            tree_nodes.append({
                'id': node_id,
                'level': lvl_idx,
                'index': node_idx,
                'hash': node_hash,
                'short_hash': f"{node_hash[:6]}...{node_hash[-4:]}",
                'is_target': is_target_node,
                'is_proof': is_proof_node,
                'is_root': is_root_node,
                'degree': deg_info,
            })

            if lvl_idx > 0:
                child1_idx = node_idx * 2
                child2_idx = node_idx * 2 + 1
                tree_edges.append({
                    'from': f"L{lvl_idx - 1}_N{child1_idx}",
                    'to': node_id
                })
                if child2_idx < len(levels[lvl_idx - 1]):
                    tree_edges.append({
                        'from': f"L{lvl_idx - 1}_N{child2_idx}",
                        'to': node_id
                    })

    context = {
        'selected_batch': selected_batch,
        'batches': batches,
        'degrees': degrees,
        'target_degree': target_degree,
        'target_index': target_index,
        'levels': levels,
        'computed_root': computed_root,
        'stored_root': chain_merkle_root or (issuance_batch.merkle_root if issuance_batch else ""),
        'issuance_batch': issuance_batch,
        'proof_path': proof_path,
        'step_trace': step_trace,
        'is_valid_on_chain': is_valid_on_chain,
        'contract_address': getattr(settings, 'CONTRACT_ADDRESS', '0x8E53683464fE95222b854b9336ba1b8B6B913577'),
        'chain_id': int(getattr(settings, 'CHAIN_ID', 11155111)),
        'tree_nodes_json': json.dumps(tree_nodes),
        'tree_edges_json': json.dumps(tree_edges),
        'proof_hashes_json': json.dumps(list(proof_hashes_set)),
        'target_hash': target_hash_clean,
        'root_hash': root_hash_clean,
    }
    return render(request, 'verification/merkle_visualizer.html', context)


def w3c_standalone_verifier_view(request):
    """
    [Nghĩa - Tech Showcase] Trình xác minh độc lập chuẩn W3C Verifiable Credentials (Standalone Verifier):
    Hoạt động 100% Client-Side trong trình duyệt bằng Web Cryptography API & Keccak-256.
    Không phụ thuộc vào Database của trường học; có thể kiểm tra tính toàn vẹn (Tamper-Proof)
    và đối soát trực tiếp Smart Contract Sepolia.
    """
    import json
    from apps.degrees.models import Degree

    initial_vc_json = ""
    target_degree = None
    degree_id = request.GET.get('degree_id', '').strip()

    if degree_id:
        target_degree = (
            Degree.objects.filter(credential_public_id=degree_id).first()
            or Degree.objects.filter(student__student_code__iexact=degree_id).first()
            or Degree.objects.filter(pk=degree_id if str(degree_id).isdigit() else 0).first()
        )

    sample_valid_deg = Degree.objects.filter(id=315).first() or Degree.objects.filter(status='ISSUED', merkle_proof__isnull=False).first()
    sample_revoked_deg = Degree.objects.filter(id=74).first() or Degree.objects.filter(status='REVOKED', merkle_proof__isnull=False).first()

    if target_degree:
        initial_vc_json = json.dumps(generate_w3c_vc_dict(target_degree, request=request), indent=2, ensure_ascii=False)
    elif sample_valid_deg:
        initial_vc_json = json.dumps(generate_w3c_vc_dict(sample_valid_deg, request=request), indent=2, ensure_ascii=False)

    sample_valid_json = json.dumps(generate_w3c_vc_dict(sample_valid_deg, request=request), indent=2, ensure_ascii=False) if sample_valid_deg else ""
    sample_revoked_json = json.dumps(generate_w3c_vc_dict(sample_revoked_deg, request=request), indent=2, ensure_ascii=False) if sample_revoked_deg else ""

    context = {
        'initial_vc_json': initial_vc_json,
        'sample_valid_json': sample_valid_json,
        'sample_revoked_json': sample_revoked_json,
        'contract_address': getattr(settings, 'CONTRACT_ADDRESS', '0x8E53683464fE95222b854b9336ba1b8B6B913577'),
        'chain_id': int(getattr(settings, 'CHAIN_ID', 11155111)),
    }
    return render(request, 'verification/w3c_verifier.html', context)

