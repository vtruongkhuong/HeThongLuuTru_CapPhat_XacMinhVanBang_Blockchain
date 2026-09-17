"""
Trang Dashboard sau khi đăng nhập - tổng quan hệ thống + lối tắt tới từng module.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.students.models import Student, ImportBatch
from apps.academic.models import Faculty, Major


@login_required
def dashboard_view(request):
    stats = {
        'total_students': Student.objects.count(),
        'total_faculties': Faculty.objects.filter(is_active=True).count(),
        'total_majors': Major.objects.filter(is_active=True).count(),
        'recent_imports': ImportBatch.objects.select_related('imported_by').order_by('-created_at')[:5],
    }
    return render(request, 'dashboard.html', {'stats': stats})
