import io
import base64
import qrcode
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponse
from django.urls import reverse

from apps.students.models import Student
from apps.degrees.models import Degree
# Lưu ý: Sửa đường dẫn import này nếu Khương đặt get_degree_pdf ở file khác
from apps.degrees.pdf_generator import get_degree_pdf 
from .forms import StudentProfileForm

@login_required
def student_dashboard(request):
    """Hiển thị Dashboard, trạng thái văn bằng và mã QR xác thực"""
    student = getattr(request.user, 'student_profile', None)
    degree = None
    qr_code_base64 = None
    verify_url = None
    
    if student:
        degree = Degree.objects.filter(student=student).first()
        if degree:
            # Lấy mã định danh công khai của văn bằng (ưu tiên credential_public_id)
            public_id = getattr(degree, 'credential_public_id', None) or getattr(degree, 'serial_number', '')
            
            # Tạo đường dẫn xác thực đầy đủ (VD: http://127.0.0.1:8000/verify/?q=...)
            verify_url = request.build_absolute_uri(f"/?q={public_id}")
            
            # Sinh mã QR dạng Base64
            qr = qrcode.QRCode(version=1, box_size=10, border=2)
            qr.add_data(verify_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="#112953", back_color="white")
            
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            qr_code_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
    return render(request, 'student_portal/dashboard.html', {
        'student': student,
        'degree': degree,
        'qr_code_base64': qr_code_base64,
        'verify_url': verify_url,
    })

@login_required
def update_profile_view(request):
    """Cập nhật thông tin cá nhân sinh viên"""
    student = getattr(request.user, 'student_profile', None)
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
def download_degree_pdf(request):
    """Tải văn bằng PDF thông qua hàm get_degree_pdf của Khương"""
    student = getattr(request.user, 'student_profile', None)
    if not student:
        messages.error(request, "Tài khoản chưa được liên kết hồ sơ sinh viên.")
        return redirect('student_portal:dashboard')
        
    degree = Degree.objects.filter(student=student).first()
    if not degree:
        messages.error(request, "Bạn chưa có văn bằng để tải.")
        return redirect('student_portal:dashboard')

    if degree.status == 'REVOKED':
        messages.error(request, "Văn bằng này đã bị thu hồi, không thể tải bản PDF.")
        return redirect('student_portal:dashboard')

    try:
        pdf_Output = get_degree_pdf(degree)
        filename = f"VanBang_{student.student_code}.pdf"
        
        # Xử lý linh hoạt tùy theo kiểu dữ liệu Khương trả về (Bytes, File-like object, hoặc đường dẫn)
        if isinstance(pdf_Output, (bytes, bytearray)):
            response = HttpResponse(pdf_Output, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        elif hasattr(pdf_Output, 'read'):
            return FileResponse(pdf_Output, as_attachment=True, filename=filename)
        elif isinstance(pdf_Output, str):
            return FileResponse(open(pdf_Output, 'rb'), as_attachment=True, filename=filename)
        else:
            messages.warning(request, "Phôi bằng PDF chưa sẵn sàng.")
            return redirect('student_portal:dashboard')
    except Exception as e:
        messages.warning(request, f"Không thể kết xuất PDF lúc này: {e}")
        return redirect('student_portal:dashboard')