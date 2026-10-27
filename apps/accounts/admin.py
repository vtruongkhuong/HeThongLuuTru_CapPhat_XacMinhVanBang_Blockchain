import os
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib import admin, messages
from django.shortcuts import render
from django.conf import settings

from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from apps.blockchain.client import BlockchainClient
from .models import User, Role, Permission, UserRole, RolePermission


class UserRoleInline(TabularInline):
    model = UserRole
    fk_name = 'user'
    extra = 1
    autocomplete_fields = ['role']
    tab = True


@admin.register(User)
class UserAdmin(DjangoUserAdmin, ModelAdmin):
    """Quản lý người dùng và phân quyền Blockchain trực tiếp qua MetaMask."""

    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = ('username', 'email', 'employee_code', 'department', 'wallet_address', 'display_status')
    list_filter = ('is_active', 'is_locked', 'department')
    search_fields = ('username', 'email', 'employee_code', 'wallet_address')
    inlines = [UserRoleInline]

    actions = [
        'add_admin_on_blockchain',
        'remove_admin_on_blockchain',
        'authorize_issuer_on_blockchain',
        'pause_issuer_on_blockchain',
        'unpause_issuer_on_blockchain',
        'remove_issuer_on_blockchain',
    ]

    fieldsets = DjangoUserAdmin.fieldsets + (
        ('Thông tin nghiệp vụ & Ví Web3', {
            'fields': ('employee_code', 'phone_number', 'department', 'wallet_address', 'is_locked')
        }),
    )

    @display(description="Trạng thái", label={"Hoạt động": "success", "Khóa": "danger"})
    def display_status(self, obj):
        return "Khóa" if obj.is_locked or not obj.is_active else "Hoạt động"

    def _get_contract_owner(self, contract):
        """Lấy địa chỉ ví Owner của Smart Contract để hiển thị trên giao diện MetaMask"""
        try:
            return contract.functions.owner().call()
        except Exception:
            return ""

    def _render_blockchain_action(self, request, queryset, function_name, action_label, lock_status=None):
        """Hàm dùng chung xử lý sinh calldata và mở giao diện MetaMask cho mọi hành động phân quyền"""
        if queryset.count() != 1:
            self.message_user(request, "Vui lòng chỉ chọn đúng 1 cán bộ để thao tác.", level=messages.ERROR)
            return

        target_user = queryset.first()
        wallet = target_user.wallet_address

        if not wallet or not wallet.startswith('0x') or len(wallet) != 42:
            self.message_user(request, f"Cán bộ '{target_user.username}' chưa có địa chỉ ví MetaMask hợp lệ (dạng 0x... 42 ký tự)!", level=messages.ERROR)
            return

        # Cập nhật trạng thái khóa tài khoản trên DB nếu có yêu cầu
        if lock_status is not None:
            target_user.is_locked = lock_status
            target_user.save(update_fields=['is_locked'])

        try:
            client = BlockchainClient()
            contract = client.contract
            fn = getattr(contract.functions, function_name, None)
            if not fn:
                self.message_user(request, f"Hàm '{function_name}' chưa có trên Smart Contract ABI!", level=messages.ERROR)
                return

            checksum_wallet = client.w3.to_checksum_address(wallet)
            tx_data = fn(checksum_wallet)._encode_transaction_data()

            context = {
                'action_name': action_label,
                'target_wallet': checksum_wallet,
                'target_user': target_user.username,
                'contract_address': client.contract_address,
                'contract_owner': self._get_contract_owner(contract),
                'tx_data': tx_data,
            }
            return render(request, 'admin/accounts/authorize_metamask.html', context)

        except Exception as e:
            self.message_user(request, f"Lỗi Web3: {str(e)}", level=messages.ERROR)

    # 1. Cấp quyền Quản trị viên (Admin)
    @admin.action(description="👑 1. [Blockchain] Cấp quyền QUẢN TRỊ VIÊN (addAdmin)")
    def add_admin_on_blockchain(self, request, queryset):
        return self._render_blockchain_action(
            request, queryset, 'addAdmin', 'CẤP QUYỀN QUẢN TRỊ VIÊN (addAdmin)'
        )

    # 2. Thu hồi quyền Quản trị viên (Admin)
    @admin.action(description="🚫 2. [Blockchain] Thu hồi quyền QUẢN TRỊ VIÊN (removeAdmin)")
    def remove_admin_on_blockchain(self, request, queryset):
        return self._render_blockchain_action(
            request, queryset, 'removeAdmin', 'THU HỒI QUYỀN QUẢN TRỊ VIÊN (removeAdmin)'
        )

    # 3. Cấp quyền cán bộ phát hành (Issuer)
    @admin.action(description="⚡ 3. [Blockchain] Cấp quyền cán bộ phát hành (addIssuer)")
    def authorize_issuer_on_blockchain(self, request, queryset):
        return self._render_blockchain_action(
            request, queryset, 'addIssuer', 'CẤP QUYỀN PHÁT HÀNH (addIssuer)'
        )

    # 4. Tạm khóa quyền cán bộ phát hành (Pause Issuer)
    @admin.action(description="⏸️ 4. [Blockchain] TẠM KHÓA quyền cán bộ phát hành (pauseIssuer)")
    def pause_issuer_on_blockchain(self, request, queryset):
        return self._render_blockchain_action(
            request, queryset, 'pauseIssuer', 'TẠM KHÓA CÁN BỘ PHÁT HÀNH (pauseIssuer)', lock_status=True
        )

    # 5. Mở khóa quyền cán bộ phát hành (Unpause Issuer)
    @admin.action(description="▶️ 5. [Blockchain] MỞ KHÓA quyền cán bộ phát hành (unpauseIssuer)")
    def unpause_issuer_on_blockchain(self, request, queryset):
        return self._render_blockchain_action(
            request, queryset, 'unpauseIssuer', 'MỞ KHÓA CÁN BỘ PHÁT HÀNH (unpauseIssuer)', lock_status=False
        )

    # 6. Hủy bỏ quyền cán bộ phát hành (Remove Issuer)
    @admin.action(description="❌ 6. [Blockchain] HỦY BỎ quyền cán bộ phát hành (removeIssuer)")
    def remove_issuer_on_blockchain(self, request, queryset):
        return self._render_blockchain_action(
            request, queryset, 'removeIssuer', 'GỠ QUYỀN CÁN BỘ PHÁT HÀNH (removeIssuer)'
        )


class RolePermissionInline(TabularInline):
    model = RolePermission
    extra = 1
    autocomplete_fields = ['permission']
    tab = True


@admin.register(Role)
class RoleAdmin(ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('code', 'name')
    inlines = [RolePermissionInline]


@admin.register(Permission)
class PermissionAdmin(ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('code', 'name')
