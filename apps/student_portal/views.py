import io
import base64
import qrcode
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponse

from apps.students.models import Student
from apps.degrees.models import Degree
from apps.degrees.pdf_generator import get_degree_pdf
from .forms import StudentProfileForm


def get_student_for_user(user):
    """
    Lấy hồ sơ sinh viên tương ứng với user đang đăng nhập.
    Hỗ trợ sinh viên đăng nhập bằng:
      - Tài khoản sinh viên được liên kết sẵn
      - Hoặc tài khoản Gmail / Email sinh viên có trong danh sách hồ sơ:
        Hệ thống tự động liên kết hồ sơ với tài khoản khi email trùng khớp.
    """
    if not user or not user.is_authenticated:
        return None

    student = getattr(user, 'student_profile', None)
    if not student and getattr(user, 'email', None):
        clean_email = user.email.strip().lower()
        matched = Student.objects.filter(email__iexact=clean_email).first()
        if matched:
            # Gỡ liên kết user cũ khỏi sinh viên khác (nếu có) để đảm bảo ràng buộc 1-1
            Student.objects.filter(user=user).exclude(pk=matched.pk).update(user=None)
            matched.user = user
            matched.save(update_fields=['user'])
            student = matched

    return student


@login_required
def student_dashboard(request):
    """
    Hiển thị Dashboard Cổng Sinh viên:
    - Nhận diện sinh viên qua tài khoản hoặc email/gmail đã có trong danh sách
    - Phân chia danh mục văn bằng / chứng chỉ riêng biệt:
        1. Bằng Kỹ sư (KS)
        2. Bằng Cử nhân (CN)
        3. Chứng chỉ Tin học văn phòng (THVP, CC_THVP)
        4. Chứng chỉ Công nghệ thông tin (CNTT, CC_CNTT)
    - Mỗi văn bằng có giao diện nhận diện riêng, mã QR tra cứu riêng và nút tải PDF riêng.
    """
    student = get_student_for_user(request.user)

    degrees = []
    categorized_degrees = {
        'engineer': [],    # Bằng Kỹ sư (KS)
        'bachelor': [],    # Bằng Cử nhân (CN)
        'office_it': [],   # Chứng chỉ Tin học văn phòng (THVP, CC_THVP)
        'it_cert': [],     # Chứng chỉ Công nghệ thông tin (CNTT, CC_CNTT)
        'other': [],       # Các loại khác nếu có
    }

    counts = {
        'all': 0,
        'engineer': 0,
        'bachelor': 0,
        'office_it': 0,
        'it_cert': 0,
        'other': 0,
    }

    if student:
        all_degrees = Degree.objects.filter(student=student).select_related(
            'batch', 'degree_type', 'student__major__faculty'
        ).order_by('-issue_date', '-id')

        for deg in all_degrees:
            # Sinh verify URL và QR Code riêng cho từng văn bằng
            pub_id = getattr(deg, 'credential_public_id', None) or getattr(deg, 'serial_number', '') or str(deg.id)
            verify_url = request.build_absolute_uri(f"/?q={pub_id}")

            qr = qrcode.QRCode(version=1, box_size=8, border=2)
            qr.add_data(verify_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="#112953", back_color="white")

            buf = io.BytesIO()
            img.save(buf, format="PNG")
            qr_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

            deg_item = {
                'obj': deg,
                'verify_url': verify_url,
                'qr_code_base64': qr_base64,
            }

            code = (deg.degree_type.code if deg.degree_type and deg.degree_type.code else '').upper()
            if code in ('KS', 'KY_SU'):
                deg_item['category'] = 'engineer'
                deg_item['badge_label'] = 'BẰNG KỸ SƯ'
                deg_item['theme_color'] = 'blue'
                categorized_degrees['engineer'].append(deg_item)
                counts['engineer'] += 1
            elif code in ('CN', 'CU_NHAN'):
                deg_item['category'] = 'bachelor'
                deg_item['badge_label'] = 'BẰNG CỬ NHÂN'
                deg_item['theme_color'] = 'red'
                categorized_degrees['bachelor'].append(deg_item)
                counts['bachelor'] += 1
            elif code in ('THVP', 'CC_THVP', 'TIN_HOC_VP'):
                deg_item['category'] = 'office_it'
                deg_item['badge_label'] = 'CHỨNG CHỈ TIN HỌC VĂN PHÒNG'
                deg_item['theme_color'] = 'emerald'
                categorized_degrees['office_it'].append(deg_item)
                counts['office_it'] += 1
            elif code in ('CNTT', 'CC_CNTT', 'CONG_NGHE_TT'):
                deg_item['category'] = 'it_cert'
                deg_item['badge_label'] = 'CHỨNG CHỈ CÔNG NGHỆ THÔNG TIN'
                deg_item['theme_color'] = 'purple'
                categorized_degrees['it_cert'].append(deg_item)
                counts['it_cert'] += 1
            else:
                deg_item['category'] = 'other'
                deg_item['badge_label'] = deg.degree_type.name if deg.degree_type else 'VĂN BẰNG'
                deg_item['theme_color'] = 'gray'
                categorized_degrees['other'].append(deg_item)
                counts['other'] += 1

            degrees.append(deg_item)
            counts['all'] += 1

    return render(request, 'student_portal/dashboard.html', {
        'student': student,
        'degrees': degrees,
        'categorized_degrees': categorized_degrees,
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
def download_degree_pdf(request, degree_id=None):
    """
    Tải văn bằng PDF theo từng văn bằng cụ thể của sinh viên
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
