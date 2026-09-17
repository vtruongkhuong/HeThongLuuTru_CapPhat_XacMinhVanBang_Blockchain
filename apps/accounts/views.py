from django.contrib.auth import login, logout, update_session_auth_hash, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView as DjangoLoginView

from .forms import LoginForm, ChangePasswordForm, UserProfileForm


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
        # Lấy dữ liệu từ form HTML
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')

        # 1. Kiểm tra mật khẩu có khớp không
        if password != password_confirm:
            messages.error(request, 'Mật khẩu xác nhận không khớp.')
            return render(request, 'accounts/register.html')

        # 2. Kiểm tra tên đăng nhập đã tồn tại chưa
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Tên đăng nhập này đã được sử dụng.')
            return render(request, 'accounts/register.html')

        # 3. Tạo tài khoản mới
        user = User.objects.create_user(username=username, email=email, password=password)
        
        # 4. Tự động đăng nhập
        login(request, user)
        messages.success(request, 'Đăng ký thành công! Chào mừng bạn.')
        
        # 5. Chuyển hướng vào trang danh sách sinh viên
        return redirect('students:student_list')

    # Nếu là phương thức GET thì chỉ hiển thị giao diện form
    return render(request, 'accounts/register.html')
