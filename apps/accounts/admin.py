from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from django.contrib import admin, messages 
from django.shortcuts import render
from django.conf import settings 
import web3 
import json 
import os
from .models import User, Role, Permission, UserRole, RolePermission


class UserRoleInline(TabularInline):
    model = UserRole
    fk_name = 'user'
    extra = 1
    autocomplete_fields = ['role']
    tab = True


@admin.register(User)
class UserAdmin(DjangoUserAdmin, ModelAdmin):
    """Quản lý người dùng và quyền Issuer trên Blockchain."""

    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = ('username', 'email', 'employee_code', 'department', 'wallet_address', 'display_status')
    list_filter = ('is_active', 'is_locked', 'department')
    search_fields = ('username', 'email', 'employee_code')
    inlines = [UserRoleInline]

    actions = [
        'authorize_issuer_on_blockchain',
        'pause_issuer_on_blockchain',
        'unpause_issuer_on_blockchain',
        'remove_issuer_on_blockchain',
    ]
    
    fieldsets = DjangoUserAdmin.fieldsets + (
        ('Thông tin nghiệp vụ', {
            'fields': ('employee_code', 'phone_number', 'department', 'wallet_address', 'is_locked')
        }),
    )

    @display(description="Trạng thái", label={"Hoạt động": "success", "Khóa": "danger"})
    def display_status(self, obj):
        return "Khóa" if obj.is_locked or not obj.is_active else "Hoạt động"

    def _get_contract(self):
        w3 = web3.Web3()
        contract_address = getattr(settings, 'CONTRACT_ADDRESS', '0xEDA267AE063b32A8b23B97e67a5dD355891cbd1D')
        abi_path = os.path.join(settings.BASE_DIR, 'apps', 'blockchain', 'contracts_abi', 'DegreeVerification.json')
        with open(abi_path, 'r', encoding='utf-8') as f:
            abi = json.load(f)
        return w3.eth.contract(address=w3.to_checksum_address(contract_address), abi=abi), contract_address

    @admin.action(description="[Blockchain] Cấp quyền cán bộ phát hành (addIssuer)")
    def authorize_issuer_on_blockchain(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Vui lòng chọn đúng 1 cán bộ để cấp quyền.", level=messages.ERROR)
            return
            
        user_to_authorize = queryset.first()
        wallet = user_to_authorize.wallet_address
        if not wallet or not wallet.startswith('0x') or len(wallet) != 42:
            self.message_user(request, "Cán bộ này chưa có địa chỉ ví hợp lệ!", level=messages.ERROR)
            return

        try:
            contract, contract_address = self._get_contract()
            tx_data = contract.functions.addIssuer(wallet)._encode_transaction_data()
            context = {
                'action_name': 'CẤP QUYỀN PHÁT HÀNH (addIssuer)',
                'target_wallet': wallet,
                'target_user': user_to_authorize.username,
                'contract_address': contract_address,
                'contract_owner': self._get_contract_owner(contract),
                'tx_data': tx_data,
            }
            return render(request, 'admin/accounts/authorize_metamask.html', context)
        except Exception as e:
            self.message_user(request, f"Lỗi Web3: {str(e)}", level=messages.ERROR)

    @admin.action(description="[Blockchain] TẠM KHÓA quyền cán bộ phát hành (pauseIssuer)")
    def pause_issuer_on_blockchain(self, request, queryset):
        """[N7] Chủ trường tạm khóa một cán bộ thì cán bộ đó không ký phát hành được nữa"""
        if queryset.count() != 1:
            self.message_user(request, "Vui lòng chọn đúng 1 cán bộ để tạm khóa.", level=messages.ERROR)
            return

        target_user = queryset.first()
        wallet = target_user.wallet_address
        if not wallet or not wallet.startswith('0x') or len(wallet) != 42:
            self.message_user(request, "Cán bộ này chưa có địa chỉ ví hợp lệ!", level=messages.ERROR)
            return

        # Cập nhật cờ is_locked trên cơ sở dữ liệu
        target_user.is_locked = True
        target_user.save(update_fields=['is_locked'])

        try:
            contract, contract_address = self._get_contract()
            tx_data = contract.functions.pauseIssuer(wallet)._encode_transaction_data()
            context = {
                'action_name': 'TẠM KHÓA CÁN BỘ PHÁT HÀNH (pauseIssuer)',
                'target_wallet': wallet,
                'target_user': target_user.username,
                'contract_address': contract_address,
                'contract_owner': self._get_contract_owner(contract),
                'tx_data': tx_data,
            }
            return render(request, 'admin/accounts/authorize_metamask.html', context)
        except Exception as e:
            self.message_user(request, f"Lỗi Web3: {str(e)}", level=messages.ERROR)

    @admin.action(description="[Blockchain] MỞ KHÓA quyền cán bộ phát hành (unpauseIssuer)")
    def unpause_issuer_on_blockchain(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Vui lòng chọn đúng 1 cán bộ để mở khóa.", level=messages.ERROR)
            return

        target_user = queryset.first()
        wallet = target_user.wallet_address
        if not wallet or not wallet.startswith('0x') or len(wallet) != 42:
            self.message_user(request, "Cán bộ này chưa có địa chỉ ví hợp lệ!", level=messages.ERROR)
            return

        target_user.is_locked = False
        target_user.save(update_fields=['is_locked'])

        try:
            contract, contract_address = self._get_contract()
            tx_data = contract.functions.unpauseIssuer(wallet)._encode_transaction_data()
            context = {
                'action_name': 'MỞ KHÓA CÁN BỘ PHÁT HÀNH (unpauseIssuer)',
                'target_wallet': wallet,
                'target_user': target_user.username,
                'contract_address': contract_address,
                'contract_owner': self._get_contract_owner(contract),
                'tx_data': tx_data,
            }
            return render(request, 'admin/accounts/authorize_metamask.html', context)
        except Exception as e:
            self.message_user(request, f"Lỗi Web3: {str(e)}", level=messages.ERROR)

    @admin.action(description="[Blockchain] HỦY BỎ quyền cán bộ phát hành (removeIssuer)")
    def remove_issuer_on_blockchain(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Vui lòng chọn đúng 1 cán bộ để gỡ quyền.", level=messages.ERROR)
            return

        target_user = queryset.first()
        wallet = target_user.wallet_address
        if not wallet or not wallet.startswith('0x') or len(wallet) != 42:
            self.message_user(request, "Cán bộ này chưa có địa chỉ ví hợp lệ!", level=messages.ERROR)
            return

        try:
            contract, contract_address = self._get_contract()
            tx_data = contract.functions.removeIssuer(wallet)._encode_transaction_data()
            context = {
                'action_name': 'GỠ QUYỀN CÁN BỘ PHÁT HÀNH (removeIssuer)',
                'target_wallet': wallet,
                'target_user': target_user.username,
                'contract_address': contract_address,
                'contract_owner': self._get_contract_owner(contract),
                'tx_data': tx_data,
            }
            return render(request, 'admin/accounts/authorize_metamask.html', context)
        except Exception as e:
            self.message_user(request, f"Lỗi Web3: {str(e)}", level=messages.ERROR)


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
