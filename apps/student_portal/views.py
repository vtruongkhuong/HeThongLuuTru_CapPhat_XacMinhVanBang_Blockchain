import io
import json
import base64
import qrcode
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponse, JsonResponse
from django.conf import settings
from django.utils import timezone

from apps.students.models import Student
from apps.degrees.models import Degree
from apps.degrees.pdf_generator import get_degree_pdf
from apps.blockchain.models import DegreeMerkleProof, BlockchainTransaction
from .forms import StudentProfileForm


def get_student_for_user(user):
    """
    Lấy hồ sơ sinh viên tương ứng với user đang đăng nhập.
    Tự động liên kết khi email trùng khớp theo nhiệm vụ N4.
    """
    if not user or not user.is_authenticated:
        return None

    student = getattr(user, 'student_profile', None)
    if not student and getattr(user, 'email', None):
        clean_email = user.email.strip().lower()
        matched = Student.objects.filter(email__iexact=clean_email).first()
        if matched:
            Student.objects.filter(user=user).exclude(pk=matched.pk).update(user=None)
            matched.user = user
            matched.save(update_fields=['user'])
            student = matched

    return student


@login_required
def student_dashboard(request):
    """
    [N5] Dashboard Cổng Sinh viên:
    - Truy vấn toàn bộ văn bằng/chứng chỉ của sinh viên: degree_list = student.degrees.filter(status='ISSUED')
    - Thiết kế giao diện theo 2 khu vực rõ ràng:
        📂 Khu vực 1: Văn bằng tốt nghiệp Đại học (Cử nhân, Kỹ sư).
        📂 Khu vực 2: Chứng chỉ Tin học & Công nghệ (Tin học văn phòng, CNTT...).
    - Mỗi văn bằng có thẻ card đẹp mắt, mã QR riêng, nút xem trước, nút tải PDF đúng mẫu và nút tải JSON xác minh độc lập.
    """
    student = get_student_for_user(request.user)

    degrees = []
    university_degrees = []  # Khu vực 1: Bằng tốt nghiệp ĐH (CN, KS)
    certifications = []      # Khu vực 2: Chứng chỉ Tin học & Công nghệ (THVP, CNTT)
    other_degrees = []       # Các loại khác nếu có

    counts = {
        'all': 0,
        'engineer': 0,
        'bachelor': 0,
        'office_it': 0,
        'it_cert': 0,
        'other': 0,
        'university': 0,
        'certifications': 0,
    }

    if student:
        # Truy vấn toàn bộ văn bằng/chứng chỉ của sinh viên
        all_degrees = Degree.objects.filter(student=student).select_related(
            'batch', 'degree_type', 'student__major__faculty'
        ).order_by('-issue_date', '-id')

        for deg in all_degrees:
            pub_id = getattr(deg, 'credential_public_id', None) or getattr(deg, 'serial_number', '') or str(deg.id)
            verify_url = request.build_absolute_uri(f"/verify/tracuu/?q={pub_id}")

            # Tạo mã QR Code sắc nét
            qr = qrcode.QRCode(version=1, box_size=8, border=2)
            qr.add_data(verify_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="#112953", back_color="white")

            buf = io.BytesIO()
            img.save(buf, format="PNG")
            qr_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

            # Tra cứu giao dịch Blockchain nếu có
            tx_obj = BlockchainTransaction.objects.filter(degree=deg, status='confirmed').first()
            tx_hash = getattr(tx_obj, 'tx_hash', None) or getattr(deg, 'tx_hash', None)
            etherscan_url = f"https://sepolia.etherscan.io/tx/{tx_hash}" if tx_hash else None

            deg_item = {
                'obj': deg,
                'verify_url': verify_url,
                'qr_code_base64': qr_base64,
                'tx_hash': tx_hash,
                'etherscan_url': etherscan_url,
            }

            code = (deg.degree_type.code if deg.degree_type and deg.degree_type.code else '').upper()

            # Phân chia 2 khu vực danh mục chuẩn xác
            if code in ('KS', 'KY_SU'):
                deg_item['category'] = 'engineer'
                deg_item['badge_label'] = 'BẰNG KỸ SƯ CHÍNH QUY'
                deg_item['theme_color'] = 'blue'
                university_degrees.append(deg_item)
                counts['engineer'] += 1
                counts['university'] += 1
            elif code in ('CN', 'CU_NHAN'):
                deg_item['category'] = 'bachelor'
                deg_item['badge_label'] = 'BẰNG CỬ NHÂN CHÍNH QUY'
                deg_item['theme_color'] = 'red'
                university_degrees.append(deg_item)
                counts['bachelor'] += 1
                counts['university'] += 1
            elif code in ('THVP', 'CC_THVP', 'TIN_HOC_VP'):
                deg_item['category'] = 'office_it'
                deg_item['badge_label'] = 'CHỨNG CHỈ TIN HỌC VĂN PHÒNG'
                deg_item['theme_color'] = 'emerald'
                certifications.append(deg_item)
                counts['office_it'] += 1
                counts['certifications'] += 1
            elif code in ('CNTT', 'CC_CNTT', 'CONG_NGHE_TT'):
                deg_item['category'] = 'it_cert'
                deg_item['badge_label'] = 'CHỨNG CHỈ CÔNG NGHỆ THÔNG TIN'
                deg_item['theme_color'] = 'purple'
                certifications.append(deg_item)
                counts['it_cert'] += 1
                counts['certifications'] += 1
            else:
                deg_item['category'] = 'other'
                deg_item['badge_label'] = deg.degree_type.name if deg.degree_type else 'VĂN BẰNG'
                deg_item['theme_color'] = 'gray'
                other_degrees.append(deg_item)
                counts['other'] += 1

            degrees.append(deg_item)
            counts['all'] += 1

    return render(request, 'student_portal/dashboard.html', {
        'student': student,
        'degrees': degrees,
        'university_degrees': university_degrees,
        'certifications': certifications,
        'other_degrees': other_degrees,
        'counts': counts,
    })


@login_required
def update_profile_view(request):
    """Cập nhật thông tin cá nhân sinh viên"""
    student = get_student_for_user(request.user)
    if not student:
        messages.error(request, "Tài khoản chưa được liên kết với hồ sơ sinh viên!")
        return redirect('landing')

    if request.method == 'POST':
        form = StudentProfileForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, "Cập nhật hồ sơ cá nhân thành công!")
            return redirect('student_portal:dashboard')
    else:
        form = StudentProfileForm(instance=student)

    return render(request, 'student_portal/profile_update.html', {
        'form': form,
        'student': student
    })


@login_required
def preview_degree_pdf(request, degree_id):
    """
    [N5] Xem trước PDF văn bằng trực tiếp trên trình duyệt
    """
    student = get_student_for_user(request.user)
    if not student:
        messages.error(request, "Tài khoản chưa được liên kết hồ sơ sinh viên.")
        return redirect('student_portal:dashboard')

    degree = get_object_or_404(Degree, pk=degree_id, student=student)

    try:
        pdf_output = get_degree_pdf(degree)
        if isinstance(pdf_output, (bytes, bytearray)):
            response = HttpResponse(pdf_output, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="preview_{degree.id}.pdf"'
            return response
        elif hasattr(pdf_output, 'read'):
            return FileResponse(pdf_output, content_type='application/pdf')
        elif isinstance(pdf_output, str):
            return FileResponse(open(pdf_output, 'rb'), content_type='application/pdf')
    except Exception as e:
        messages.warning(request, f"Không thể xem trước PDF lúc này: {e}")
    return redirect('student_portal:dashboard')


@login_required
def download_degree_pdf(request, degree_id=None):
    """
    [N5] Tải văn bằng PDF theo từng văn bằng cụ thể của sinh viên
    """
    student = get_student_for_user(request.user)
    if not student:
        messages.error(request, "Tài khoản chưa được liên kết hồ sơ sinh viên.")
        return redirect('student_portal:dashboard')

    if degree_id:
        degree = Degree.objects.filter(student=student, id=degree_id).first()
    else:
        degree = Degree.objects.filter(student=student).first()

    if not degree:
        messages.error(request, "Không tìm thấy văn bằng/chứng chỉ để tải.")
        return redirect('student_portal:dashboard')

    if degree.status == 'REVOKED':
        messages.error(request, "Văn bằng/chứng chỉ này đã bị thu hồi, không thể tải bản PDF.")
        return redirect('student_portal:dashboard')

    try:
        pdf_output = get_degree_pdf(degree)
        type_code = (degree.degree_type.code if degree.degree_type else 'VB').upper()
        filename = f"{type_code}_{student.student_code}_{degree.id}.pdf"

        if isinstance(pdf_output, (bytes, bytearray)):
            response = HttpResponse(pdf_output, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        elif hasattr(pdf_output, 'read'):
            return FileResponse(pdf_output, as_attachment=True, filename=filename)
        elif isinstance(pdf_output, str):
            return FileResponse(open(pdf_output, 'rb'), as_attachment=True, filename=filename)
        else:
            messages.warning(request, "Phôi bằng PDF chưa sẵn sàng.")
            return redirect('student_portal:dashboard')
    except Exception as e:
        messages.warning(request, f"Không thể kết xuất PDF lúc này: {e}")
        return redirect('student_portal:dashboard')


@login_required
def download_verification_package(request, degree_id):
    """
    [N5] Tải gói xác minh độc lập (JSON Verification Package):
    Chứa đầy đủ: Dữ liệu văn bằng, Merkle Leaf, Proof Path, Merkle Root, Contract Address, TxHash
    Cho phép bên thứ ba tự xác minh tính toàn vẹn độc lập mà không cần truy cập Database.
    """
    student = get_student_for_user(request.user)
    if not student:
        messages.error(request, "Tài khoản chưa được liên kết hồ sơ sinh viên.")
        return redirect('student_portal:dashboard')

    degree = get_object_or_404(Degree, pk=degree_id, student=student)

    # 1. Lấy thông tin Merkle Proof
    proof_obj = DegreeMerkleProof.objects.filter(degree=degree).first()
    proof_path = proof_obj.proof_path if proof_obj and proof_obj.proof_path else []
    leaf_hash = getattr(proof_obj, 'leaf_hash', None) or degree.canonical_hash

    # 2. Lấy thông tin đợt cấp phát & Smart Contract
    issuance_batch = getattr(proof_obj, 'issuance_batch', None)
    if not issuance_batch and hasattr(degree, 'batch') and degree.batch:
        issuance_batch = degree.batch.issuance_batches.filter(status='CONFIRMED').first()

    merkle_root = getattr(issuance_batch, 'merkle_root', '') if issuance_batch else ''
    chain_batch_id = getattr(issuance_batch, 'chain_id', '') if issuance_batch else ''

    tx_record = BlockchainTransaction.objects.filter(degree=degree, status='confirmed').first()
    tx_hash = getattr(tx_record, 'tx_hash', None) or getattr(degree, 'tx_hash', None)

    package = {
        "format": "CTUT-Degree-Verification-Package-v2",
        "credential_public_id": str(degree.credential_public_id),
        "exported_at": timezone.now().isoformat(),
        "student": {
            "student_code": student.student_code,
            "full_name": student.full_name,
            "date_of_birth": str(student.date_of_birth) if student.date_of_birth else None,
            "national_id": student.national_id,
        },
        "degree": {
            "type_code": degree.degree_type.code if degree.degree_type else None,
            "type_name": degree.degree_type.name if degree.degree_type else None,
            "classification": degree.classification,
            "issue_date": str(degree.issue_date) if degree.issue_date else None,
            "serial_number": getattr(degree, 'serial_number', None) or str(degree.id),
            "status": degree.status,
        },
        "cryptographic_proof": {
            "canonical_hash": degree.canonical_hash,
            "merkle_leaf": leaf_hash,
            "merkle_root": merkle_root,
            "proof_path": proof_path,
        },
        "blockchain_anchor": {
            "network": "Ethereum Sepolia Testnet",
            "chain_id": int(getattr(settings, 'CHAIN_ID', 11155111)),
            "contract_address": getattr(settings, 'CONTRACT_ADDRESS', ''),
            "batch_id": chain_batch_id,
            "tx_hash": tx_hash,
            "explorer_url": f"https://sepolia.etherscan.io/tx/{tx_hash}" if tx_hash else None,
        },
        "verification_endpoint": request.build_absolute_uri(f"/verify/tracuu/?q={degree.credential_public_id}"),
    }

    response = HttpResponse(
        json.dumps(package, indent=2, ensure_ascii=False),
        content_type='application/json; charset=utf-8'
    )
    filename = f"VerificationPackage_{student.student_code}_{degree.id}.json"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
