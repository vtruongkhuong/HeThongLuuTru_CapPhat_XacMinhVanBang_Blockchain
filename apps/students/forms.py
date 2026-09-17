from django import forms

from .models import Student, ImportBatch

INPUT_CLS = (
    "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm "
    "focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
)
SELECT_CLS = INPUT_CLS
FILE_CLS = (
    "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm bg-white "
    "file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 "
    "file:bg-primary-50 file:text-primary-700 file:text-sm file:font-medium "
    "hover:file:bg-primary-100"
)


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            'student_code', 'full_name', 'date_of_birth', 'gender',
            'national_id', 'email', 'phone_number',
            'faculty', 'major', 'enrollment_year',
        ]
        widgets = {
            'student_code': forms.TextInput(attrs={'class': INPUT_CLS}),
            'full_name': forms.TextInput(attrs={'class': INPUT_CLS}),
            'date_of_birth': forms.DateInput(attrs={'class': INPUT_CLS, 'type': 'date'}),
            'gender': forms.Select(attrs={'class': SELECT_CLS}),
            'national_id': forms.TextInput(attrs={'class': INPUT_CLS}),
            'email': forms.EmailInput(attrs={'class': INPUT_CLS}),
            'phone_number': forms.TextInput(attrs={'class': INPUT_CLS}),
            'faculty': forms.Select(attrs={'class': SELECT_CLS}),
            'major': forms.Select(attrs={'class': SELECT_CLS}),
            'enrollment_year': forms.NumberInput(attrs={'class': INPUT_CLS}),
        }


class StudentSearchForm(forms.Form):
    """Form tìm kiếm sinh viên trên trang danh sách."""

    keyword = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': INPUT_CLS,
            'placeholder': 'Tìm theo mã SV, họ tên, CCCD...'
        }),
    )
    faculty = forms.ModelChoiceField(
        queryset=None, required=False,
        widget=forms.Select(attrs={'class': SELECT_CLS}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.academic.models import Faculty
        self.fields['faculty'].queryset = Faculty.objects.filter(is_active=True)
        self.fields['faculty'].empty_label = "-- Tất cả Khoa --"


class StudentImportForm(forms.ModelForm):
    """Form upload file Excel/CSV để import hàng loạt sinh viên."""
    
    # Khai báo một trường File mới ở tầng Form (không lưu trực tiếp vào db)
    upload_file = forms.FileField(
        label="Chọn file Excel/CSV",
        widget=forms.ClearableFileInput(attrs={
            'class': FILE_CLS,
            'accept': '.csv,.xlsx,.xls',
        })
    )

    class Meta:
        model = ImportBatch
        fields = [] # Chúng ta sẽ gán các trường batch, mode thủ công ở views

    def clean_upload_file(self):
        file = self.cleaned_data['upload_file']
        allowed_ext = ('.csv', '.xlsx', '.xls')
        if not file.name.lower().endswith(allowed_ext):
            raise forms.ValidationError("Chỉ chấp nhận file .csv, .xlsx hoặc .xls")
        max_size_mb = 10
        if file.size > max_size_mb * 1024 * 1024:
            raise forms.ValidationError(f"File vượt quá {max_size_mb}MB")
        return file