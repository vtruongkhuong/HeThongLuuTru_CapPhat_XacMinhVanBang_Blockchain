from django import forms
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm, UserCreationForm

from .models import User

# Class Tailwind dùng chung cho input, để đồng bộ giao diện toàn hệ thống
INPUT_CLS = (
    "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm "
    "focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
)


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': INPUT_CLS, 'autofocus': True})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': INPUT_CLS})
    )

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if user.is_locked:
            raise forms.ValidationError(
                "Tài khoản của bạn đã bị khóa. Vui lòng liên hệ quản trị viên.",
                code='account_locked',
            )


class ChangePasswordForm(SetPasswordForm):
    """Đổi mật khẩu khi đã đăng nhập (yêu cầu nhập mật khẩu cũ)."""

    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': INPUT_CLS}),
        label="Mật khẩu hiện tại",
    )

    def clean_old_password(self):
        old_password = self.cleaned_data['old_password']
        if not self.user.check_password(old_password):
            raise forms.ValidationError("Mật khẩu hiện tại không đúng.", code='password_incorrect')
        return old_password

    field_order = ['old_password', 'new_password1', 'new_password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].widget.attrs['class'] = INPUT_CLS
        self.fields['new_password2'].widget.attrs['class'] = INPUT_CLS


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'department']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': INPUT_CLS}),
            'last_name': forms.TextInput(attrs={'class': INPUT_CLS}),
            'email': forms.EmailInput(attrs={'class': INPUT_CLS}),
            'phone_number': forms.TextInput(attrs={'class': INPUT_CLS}),
            'department': forms.TextInput(attrs={'class': INPUT_CLS}),
        }

class RegisterForm(UserCreationForm):
    """Form đăng ký người dùng mới, tự động kiểm tra độ mạnh mật khẩu và xử lý giao diện."""
    email = forms.EmailField(
        required=True, 
        widget=forms.EmailInput(attrs={'class': INPUT_CLS})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'email'] # Mật khẩu sẽ được UserCreationForm tự động thêm vào

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email này đã được sử dụng.", code='email_exists')
        return email

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Áp dụng class Tailwind cho tất cả các input (bao gồm cả username, password)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = INPUT_CLS