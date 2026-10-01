from django import forms
from apps.students.models import Student

class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['avatar', 'current_address', 'personal_link']