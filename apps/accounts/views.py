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
    return render(request, 'accounts/profile.html', {'form': form, 'user_roles': request.user.roles.all() if request.user.is_authenticated else []})


User = get_user_model()

def register_view(request):
    # Nếu người dùng đã đăng nhập thì không cho vào trang đăng ký nữa
    if request.user.is_authenticated:
        return redirect('accounts:landing')

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
            return redirect('landing')
        else:
            # Nếu có lỗi (mật khẩu yếu, trùng tên...), hiển thị thông báo lỗi chung
            messages.error(request, 'Đăng ký thất bại. Vui lòng kiểm tra lại thông tin bên dưới.')
    else:
        # Nếu là phương thức GET thì tạo form trống
        form = RegisterForm()

    # Truyền biến 'form' ra giao diện
    return render(request, 'accounts/register.html', {'form': form})


import json
import secrets
from django.http import JsonResponse
from eth_account.messages import encode_defunct
from web3 import Web3


def web3_nonce_view(request):
    """Sinh chuỗi ngẫu nhiên (Nonce) chống tấn công Replay Attack khi đăng nhập Web3."""
    nonce = secrets.token_hex(16)
    request.session['web3_nonce'] = nonce
    return JsonResponse({'nonce': nonce})


def web3_login_view(request):
    """
    Xác thực chữ ký số MetaMask theo chuẩn SIWE (EIP-4361):
    1. Kiểm tra nonce hợp lệ trong session.
    2. Giải mã chữ ký (recover address) từ thông điệp.
    3. Đăng nhập user tương ứng hoặc tạo mới tài khoản Web3.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Phương thức không được hỗ trợ.'}, status=405)

    try:
        data = json.loads(request.body)
        address = (data.get('address') or '').strip()
        signature = (data.get('signature') or '').strip()
        message = data.get('message') or ''

        if not address or not signature or not message:
            return JsonResponse({'success': False, 'error': 'Thiếu tham số xác thực (address, signature, message).'}, status=400)

        stored_nonce = request.session.get('web3_nonce')
        if not stored_nonce or stored_nonce not in message:
            return JsonResponse({'success': False, 'error': 'Mã nonce không hợp lệ hoặc đã hết hạn.'}, status=400)

        # 1. Giải mã chữ ký để lấy địa chỉ ví thực tế
        msg_encoded = encode_defunct(text=message)
        w3 = Web3()
        recovered_address = w3.eth.account.recover_message(msg_encoded, signature=signature)

        if recovered_address.lower() != address.lower():
            return JsonResponse({'success': False, 'error': 'Chữ ký không khớp với địa chỉ ví cung cấp.'}, status=400)

        # Xóa nonce đã dùng
        request.session.pop('web3_nonce', None)

        # 2. Tìm User có wallet_address này (case-insensitive)
        user = User.objects.filter(wallet_address__iexact=recovered_address).first()

        if not user:
            # Tạo tài khoản Web3 mới nếu chưa có
            clean_addr = recovered_address.lower()
            base_username = f"web3_{clean_addr[2:8]}_{clean_addr[-4:]}"
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1

            user = User.objects.create(
                username=username,
                wallet_address=recovered_address,
                first_name='Ví Web3',
                last_name=f"{clean_addr[:6]}...{clean_addr[-4:]}",
                is_active=True
            )

        # 3. Đăng nhập người dùng vào session
        login(request, user, backend='apps.accounts.backends.EmailOrUsernameModelBackend')
        
        # Ghi log đăng nhập
        try:
            from apps.audit.services import log_action
            log_action(
                actor=user,
                action='LOGIN',
                entity_type='User',
                entity_id=str(user.id),
                new={'method': 'SIWE_METAMASK', 'wallet': recovered_address},
                request=request
            )
        except Exception:
            pass

        # Điều hướng phù hợp
        redirect_url = '/dashboard/'
        if user.is_staff or user.is_superuser:
            redirect_url = '/admin/'

        return JsonResponse({'success': True, 'redirect_url': redirect_url})

    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Lỗi xác thực Web3: {str(e)}'}, status=500)

