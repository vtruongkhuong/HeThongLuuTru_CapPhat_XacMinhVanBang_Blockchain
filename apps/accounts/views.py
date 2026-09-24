from django.contrib.auth import login, logout, update_session_auth_hash, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView as DjangoLoginView

from .forms import LoginForm, ChangePasswordForm, UserProfileForm, RegisterForm


class LoginView(DjangoLoginView):
    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "Bạn đã đăng xuất.")
    return redirect('accounts:login')


@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = ChangePasswordForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # giữ session sau khi đổi pass
            messages.success(request, "Đổi mật khẩu thành công.")
            return redirect('accounts:profile')
    else:
        form = ChangePasswordForm(user=request.user)
    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
def profile_view(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Cập nhật thông tin thành công.")
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'accounts/profile.html', {'form': form, 'user_roles': request.user.roles.all()})


User = get_user_model()

def register_view(request):
    # Nếu người dùng đã đăng nhập thì không cho vào trang đăng ký nữa
    if request.user.is_authenticated:
        return redirect('accounts:profile')

    if request.method == 'POST':
        # Giao toàn bộ dữ liệu POST cho Django Form xử lý
        form = RegisterForm(request.POST)
        
        # Hàm is_valid() sẽ tự động kiểm tra: username trùng, email trùng, password yếu, password không khớp...
        if form.is_valid():
            # Lưu user vào database
            user = form.save()
            
            # Tự động đăng nhập
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'Đăng ký thành công! Chào mừng bạn.')
            
            # Chuyển hướng vào trang danh sách sinh viên
            return redirect('dashboard')
        else:
            # Nếu có lỗi (mật khẩu yếu, trùng tên...), hiển thị thông báo lỗi chung
            messages.error(request, 'Đăng ký thất bại. Vui lòng kiểm tra lại thông tin bên dưới.')
    else:
        # Nếu là phương thức GET thì tạo form trống
        form = RegisterForm()

    # Truyền biến 'form' ra giao diện
    return render(request, 'accounts/register.html', {'form': form})
