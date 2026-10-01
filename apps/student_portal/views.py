import os
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.conf import settings

from apps.students.models import Student
from apps.degrees.models import Degree
from .forms import StudentProfileForm

@login_required
def student_dashboard(request):
    """Hàm hiển thị giao diện thẻ sinh viên (Dashboard)"""
    student = getattr(request.user, 'student_profile', None)
    degree = None
    
    if student:
        degree = Degree.objects.filter(student=student).first()
        
    return render(request, 'student_portal/dashboard.html', {
        'student': student,
        'degree': degree,
    })

@login_required
def update_profile_view(request):
    """Hàm xử lý upload ảnh và cập nhật thông tin cá nhân"""
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
    """Luồng xử lý tải văn bằng PDF cho sinh viên"""
    student = getattr(request.user, 'student_profile', None)
    if not student:
        messages.error(request, "Tài khoản chưa được liên kết hồ sơ sinh viên.")
        return redirect('student_portal:dashboard')
        
    degree = Degree.objects.filter(student=student).first()
    if not degree:
        messages.error(request, "Bạn chưa có văn bằng để tải.")
        return redirect('student_portal:dashboard')

    # Giả lập trả về file PDF (sau này Khương sẽ ghép logic tạo file thật vào đây)
    try:
        pdf_path = os.path.join(settings.MEDIA_ROOT, f'degrees/{student.student_code}.pdf') 
        return FileResponse(open(pdf_path, 'rb'), as_attachment=True, filename=f"VanBang_{student.student_code}.pdf")
    except FileNotFoundError:
        messages.warning(request, "Phôi bằng PDF đang trong quá trình kết xuất. Vui lòng thử lại sau.")
        return redirect('student_portal:dashboard')