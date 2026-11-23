import uuid
from django import forms
from django.utils import timezone
from apps.academic.models import Major, Faculty, DegreeType
from apps.students.models import Student
from apps.students.utils import get_classification_from_gpa
from apps.graduation.models import GraduationBatch
from .models import Degree
from .canonicalizer import degree_leaf_hash
from apps.workflow.services import transition
from apps.audit.services import log_action


class SingleDegreeForm(forms.Form):
    """
    Form cấp văn bằng đơn lẻ trực tiếp cho 1 sinh viên trong Django Admin.
    Hỗ trợ 2 chế độ:
    - Chọn sinh viên có sẵn trong hệ thống
    - Nhập sinh viên mới trực tiếp (không cần file Excel import)
    """
    STUDENT_MODE_CHOICES = [
        ('existing', 'Chọn sinh viên đã có trong hệ thống'),
        ('new', 'Nhập thông tin sinh viên mới trực tiếp'),
    ]

    student_mode = forms.ChoiceField(
        choices=STUDENT_MODE_CHOICES,
        initial='existing',
        widget=forms.RadioSelect(attrs={'class': 'student-mode-radio'}),
        label="Nguồn thông tin sinh viên"
    )

    # 1. Trường hợp chọn sinh viên có sẵn
    existing_student = forms.ModelChoiceField(
        queryset=Student.objects.select_related('major', 'faculty').order_by('student_code'),
        required=False,
        label="Chọn sinh viên",
        help_text="Tìm kiếm theo MSSV hoặc họ tên sinh viên đã có trong hệ thống."
    )

    # 2. Trường hợp nhập sinh viên mới trực tiếp
    student_code = forms.CharField(
        max_length=20,
        required=False,
        label="Mã số sinh viên (MSSV)",
        widget=forms.TextInput(attrs={'placeholder': 'VD: B2200123'})
    )
    full_name = forms.CharField(
        max_length=255,
        required=False,
        label="Họ và tên",
        widget=forms.TextInput(attrs={'placeholder': 'VD: Nguyễn Văn An'})
    )
    email = forms.EmailField(
        required=False,
        label="Email sinh viên",
        widget=forms.EmailInput(attrs={'placeholder': 'VD: an.b2200123@student.ctuet.edu.vn'})
    )
    date_of_birth = forms.DateField(
        required=False,
        label="Ngày sinh",
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    gender = forms.ChoiceField(
        choices=[('M', 'Nam'), ('F', 'Nữ'), ('O', 'Khác')],
        required=False,
        initial='M',
        label="Giới tính"
    )
    national_id = forms.CharField(
        max_length=20,
        required=False,
        label="Số CCCD / CMND",
        widget=forms.TextInput(attrs={'placeholder': 'VD: 092203001234'})
    )
    major = forms.ModelChoiceField(
        queryset=Major.objects.select_related('faculty', 'degree_type').all().order_by('code'),
        required=False,
        label="Ngành đào tạo"
    )
    gpa_score = forms.FloatField(
        min_value=0.0,
        max_value=4.0,
        required=False,
        label="Điểm GPA (Thang 4.0)",
        widget=forms.NumberInput(attrs={'step': '0.01', 'placeholder': 'VD: 3.45'})
    )

    # 3. Thông tin cấp văn bằng
    batch = forms.ModelChoiceField(
        queryset=GraduationBatch.objects.all().order_by('-id'),
        required=True,
        label="Đợt tốt nghiệp / Cấp chứng chỉ",
        help_text="Chọn đợt tốt nghiệp quản lý văn bằng này."
    )
    degree_type = forms.ModelChoiceField(
        queryset=DegreeType.objects.all().order_by('code'),
        required=False,
        label="Loại văn bằng / chứng chỉ",
        help_text="Để trống nếu muốn tự động lấy theo Ngành đào tạo của sinh viên."
    )
    issue_date = forms.DateField(
        required=False,
        label="Ngày cấp bằng",
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text="Mặc định lấy ngày hôm nay nếu để trống."
    )
    classification = forms.ChoiceField(
        choices=[
            ('', '-- Tự động xác định theo điểm GPA --'),
            ('Xuất sắc', 'Xuất sắc (GPA >= 3.60)'),
            ('Giỏi', 'Giỏi (3.20 <= GPA < 3.60)'),
            ('Khá', 'Khá (2.50 <= GPA < 3.20)'),
            ('Trung bình', 'Trung bình (2.00 <= GPA < 2.50)'),
        ],
        required=False,
        label="Xếp loại tốt nghiệp"
    )
    auto_submit = forms.BooleanField(
        required=False,
        initial=True,
        label="Trình duyệt ngay (Maker ➔ Checker)",
        help_text="Tự động chuyển văn bằng sang trạng thái REVIEWED (Đã thẩm định) để Lãnh đạo phê duyệt và ký phát hành On-Chain."
    )

    def clean(self):
        cleaned_data = super().clean()
        mode = cleaned_data.get('student_mode')

        if mode == 'existing':
            existing_student = cleaned_data.get('existing_student')
            if not existing_student:
                self.add_error('existing_student', 'Vui lòng chọn một sinh viên từ danh sách.')
        elif mode == 'new':
            required_new = [
                ('student_code', 'Mã số sinh viên không được để trống.'),
                ('full_name', 'Họ và tên sinh viên không được để trống.'),
                ('email', 'Email sinh viên không được để trống.'),
                ('major', 'Vui lòng chọn Ngành đào tạo cho sinh viên.'),
                ('gpa_score', 'Điểm GPA không được để trống.'),
            ]
            for field_name, msg in required_new:
                if not cleaned_data.get(field_name):
                    self.add_error(field_name, msg)

        # Kiểm tra trùng văn bằng trong cùng một đợt và kiểm tra trùng lặp loại bằng (BƯỚC 4)
        batch = cleaned_data.get('batch')
        student = None
        if mode == 'existing':
            student = cleaned_data.get('existing_student')
        elif mode == 'new' and cleaned_data.get('student_code'):
            student = Student.objects.filter(student_code=cleaned_data.get('student_code')).first()

        if student and batch:
            if Degree.objects.filter(student=student, batch=batch).exists():
                raise forms.ValidationError(
                    f"Sinh viên '{student.full_name}' ({student.student_code}) đã có văn bằng trong đợt '{batch.name}'!"
                )

        degree_type = (
            cleaned_data.get('degree_type')
            or (batch.degree_type if batch else None)
            or (student.major.degree_type if (student and student.major) else None)
        )
        if student and degree_type:
            from .services import check_duplicate_degree
            duplicate_deg = check_duplicate_degree(student, degree_type.id)
            if duplicate_deg:
                raise forms.ValidationError(
                    f"CẢNH BÁO TRÙNG LẶP: Sinh viên '{student.full_name}' ({student.student_code}) đã được cấp văn bằng '{degree_type.name}' "
                    f"(Số hiệu: {duplicate_deg.degree_number}, Trạng thái: {duplicate_deg.get_status_display()}). Không thể cấp trùng lặp!"
                )

        return cleaned_data

    def save(self, user):
        """
        Khởi tạo hoặc cập nhật sinh viên, sinh mã băm chuẩn hóa và tạo bản ghi Degree.
        """
        cleaned_data = self.cleaned_data
        mode = cleaned_data.get('student_mode')

        # 1. Xác định hoặc tạo sinh viên
        if mode == 'existing':
            student = cleaned_data.get('existing_student')
        else:
            code = cleaned_data.get('student_code').strip()
            student = Student.objects.filter(student_code=code).first()
            major = cleaned_data.get('major')
            defaults = {
                'full_name': cleaned_data.get('full_name').strip(),
                'email': cleaned_data.get('email').strip(),
                'major': major,
                'faculty': major.faculty if major else None,
                'date_of_birth': cleaned_data.get('date_of_birth'),
                'gender': cleaned_data.get('gender') or 'M',
                'national_id': cleaned_data.get('national_id', '').strip(),
                'gpa_score': cleaned_data.get('gpa_score'),
                'status': 'approved',
            }
            if student:
                for k, v in defaults.items():
                    if v is not None:
                        setattr(student, k, v)
                student.save()
            else:
                student = Student.objects.create(student_code=code, **defaults)

        # 2. Xác định Loại văn bằng
        batch = cleaned_data.get('batch')
        degree_type = (
            cleaned_data.get('degree_type') 
            or batch.degree_type 
            or (student.major.degree_type if student.major else None)
        )
        if not degree_type:
            degree_type = DegreeType.objects.filter(code='CN').first() or DegreeType.objects.first()

        # 3. Xác định Xếp loại tốt nghiệp & Ngày cấp
        classification = cleaned_data.get('classification')
        if not classification:
            classification = get_classification_from_gpa(student.gpa_score) or "Khá"

        issue_date = cleaned_data.get('issue_date') or timezone.now().date()
        pub_id = uuid.uuid4()

        # 4. Khởi tạo đối tượng Degree
        degree = Degree(
            student=student,
            batch=batch,
            degree_type=degree_type,
            credential_public_id=pub_id,
            classification=classification,
            issue_date=issue_date,
            pdf_path='',
            template_version='1.0',
            credential_version='1.0',
            status='DRAFT',
            canonical_hash='',
            reviewed_by=user if cleaned_data.get('auto_submit') else None,
            reviewed_at=timezone.now() if cleaned_data.get('auto_submit') else None,
        )
        # Sinh Canonical Hash chuẩn hóa (bao gồm GPA)
        degree.canonical_hash = degree_leaf_hash(degree)
        degree.save()

        # 5. Nếu chọn Trình duyệt ngay -> chuyển sang REVIEWED
        if cleaned_data.get('auto_submit'):
            try:
                transition(degree, 'REVIEWED', actor=user)
            except Exception:
                degree.status = 'REVIEWED'
                degree.reviewed_by = user
                degree.reviewed_at = timezone.now()
                degree.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])

        # 6. Ghi AuditLog
        try:
            log_action(
                actor=user,
                action='CREATE_SINGLE_DEGREE',
                entity_type='Degree',
                entity_id=str(degree.id),
                new={
                    'student_code': student.student_code,
                    'full_name': student.full_name,
                    'batch': batch.name,
                    'degree_type': degree_type.code,
                    'canonical_hash': degree.canonical_hash,
                    'status': degree.status
                }
            )
        except Exception:
            pass

        return degree
