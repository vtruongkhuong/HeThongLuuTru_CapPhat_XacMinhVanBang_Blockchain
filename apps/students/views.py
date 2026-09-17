from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404

from apps.core.permissions import permission_required
from .forms import StudentForm, StudentSearchForm, StudentImportForm
from .models import Student, ImportBatch


@login_required
def student_list(request):
    form = StudentSearchForm(request.GET or None)
    students = Student.objects.select_related('faculty', 'major').all()

    if form.is_valid():
        keyword = form.cleaned_data.get('keyword')
        faculty = form.cleaned_data.get('faculty')
        if keyword:
            students = students.filter(
                Q(student_code__icontains=keyword) |
                Q(full_name__icontains=keyword) |
                Q(national_id__icontains=keyword)
            )
        if faculty:
            students = students.filter(faculty=faculty)

    paginator = Paginator(students, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'students/student_list.html', {
        'form': form,
        'page_obj': page_obj,
    })


@login_required
def student_detail(request, pk):
    student = get_object_or_404(Student.objects.select_related('faculty', 'major'), pk=pk)
    return render(request, 'students/student_detail.html', {'student': student})


@login_required
@permission_required('student.import')
def student_create(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Thêm sinh viên thành công.")
            return redirect('students:student_list')
    else:
        form = StudentForm()
    return render(request, 'students/student_form.html', {'form': form})


@login_required
@permission_required('student.import')
def student_update(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, "Cập nhật sinh viên thành công.")
            return redirect('students:student_detail', pk=student.pk)
    else:
        form = StudentForm(instance=student)
    return render(request, 'students/student_form.html', {'form': form, 'student': student})


@login_required
@permission_required('student.import')
@login_required
@permission_required('student.import')
@login_required
@permission_required('student.import')
def student_import(request):
    """Upload file Excel/CSV, tạo ImportBatch, xử lý logic trực tiếp."""
    from apps.graduation.models import GraduationBatch
    from .services import process_student_import_logic # Import bộ não xử lý Excel

    if request.method == 'POST':
        form = StudentImportForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data['upload_file']
            
            # TẠM THỜI: Lấy đợt tốt nghiệp đầu tiên để test
            test_batch = GraduationBatch.objects.first()
            if not test_batch:
                messages.error(request, "Vui lòng tạo ít nhất 1 đợt tốt nghiệp (GraduationBatch) trong Admin trước khi import!")
                return redirect('students:student_import')
            
            # 1. Khởi tạo một đợt ImportBatch mới
            batch_record = ImportBatch.objects.create(
                batch=test_batch,
                file_name=uploaded_file.name,
                imported_by=request.user,
                mode='ATOMIC'
            )
            
            # 2. Quăng cái file Excel thẳng vào "bộ não" services.py để nó quét
            success, msg = process_student_import_logic(batch_record.id, uploaded_file)
            
            if success:
                messages.success(request, f"Đã quét xong file {uploaded_file.name}. Vui lòng xem chi tiết ở bảng Lịch sử.")
            else:
                messages.error(request, f"Lỗi xử lý file: {msg}")
                
            return redirect('students:import_history')
    else:
        form = StudentImportForm()
    return render(request, 'students/student_import.html', {'form': form})

@login_required
@permission_required('student.import')
def student_import_history(request):
    batches = ImportBatch.objects.select_related('imported_by').all()[:50]
    return render(request, 'students/student_import_history.html', {'batches': batches})
