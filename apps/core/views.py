"""
Trang Dashboard sau khi đăng nhập - tổng quan hệ thống + lối tắt tới từng module.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from apps.students.models import Student, ImportBatch
from apps.academic.models import Faculty, Major


@login_required
def dashboard_view(request):
    user = request.user

    # 1. Tác nhân: Super Admin -> Chuyển thẳng vào Admin Unfold
    if user.is_superuser:
        return redirect('/admin/')

    # 2. Tác nhân: Không gian Cán bộ (Có cờ is_staff = True)
    if user.is_staff:
        # Lấy danh sách mã Role của người dùng
        role_codes = user.roles.values_list('code', flat=True)

        # Cán bộ nhập liệu (Officer A) -> Tới trang Import sinh viên
        if 'academic_staff' in role_codes or 'officer_a' in role_codes:
            return redirect('admin:students_importbatch_changelist')

        # Cán bộ phê duyệt (Officer B) -> Tới trang Duyệt đợt tốt nghiệp
        elif 'reviewer' in role_codes or 'approver' in role_codes or 'officer_b' in role_codes:
            return redirect('admin:graduation_graduationbatch_changelist')

        # Cán bộ phát hành (Authorized Issuer) -> Tới trang Giao dịch Blockchain
        elif 'issuer' in role_codes:
            # Sửa lại URL name cho khớp với namespace blockchain của bạn
            return redirect('admin:blockchain_transaction_changelist') 
        
        # Cán bộ khác chưa phân vai trò cụ thể -> Cho xem trang thống kê mặc định của bạn
        stats = {
            'total_students': Student.objects.count(),
            'total_faculties': Faculty.objects.filter(is_active=True).count(),
            'total_majors': Major.objects.filter(is_active=True).count(),
            'recent_imports': ImportBatch.objects.select_related('imported_by').order_by('-created_at')[:5],
        }
        return render(request, 'dashboard.html', {'stats': stats})

    # 3. Tác nhân: Sinh viên (is_staff = False)
    # Tuyệt đối không cho xem số liệu thống kê, chuyển thẳng về trang cá nhân
    return redirect('accounts:profile')