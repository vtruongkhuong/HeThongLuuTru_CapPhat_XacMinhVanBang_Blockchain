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
    """Quản lý người dùng, dùng form + style của Unfold."""

    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = ('username', 'email', 'employee_code', 'department', 'wallet_address', 'display_status')
    list_filter = ('is_active', 'is_locked', 'department')
    search_fields = ('username', 'email', 'employee_code')
    inlines = [UserRoleInline]

    # Chỉ giữ lại 1 action gộp duy nhất
    actions = ['authorize_issuer_on_blockchain']
    
    fieldsets = DjangoUserAdmin.fieldsets + (
        ('Thông tin nghiệp vụ', {
            'fields': ('employee_code', 'phone_number', 'department', 'wallet_address', 'is_locked')
        }),
    )

    @display(description="Trạng thái", label={"Hoạt động": "success", "Khóa": "danger"})
    def display_status(self, obj):
        return "Khóa" if obj.is_locked or not obj.is_active else "Hoạt động"


    @admin.action(description="Cấp quyền PHÁT HÀNH VÀ THU HỒI lên Blockchain")
    def authorize_issuer_on_blockchain(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Vui lòng chọn 1 cán bộ để cấp quyền.", level=messages.ERROR)
            return
            
        user_to_authorize = queryset.first()
        wallet = user_to_authorize.wallet_address
        
        if not wallet or not wallet.startswith('0x') or len(wallet) != 42:
            self.message_user(request, "Cán bộ này chưa có địa chỉ ví hợp lệ!", level=messages.ERROR)
            return

        try:
            w3 = web3.Web3()
            contract_address = settings.CONTRACT_ADDRESS
            abi_path = os.path.join(settings.BASE_DIR, 'apps', 'blockchain', 'contracts_abi', 'DegreeVerification.json')
            
            with open(abi_path, 'r') as f:
                abi = json.load(f)
            contract = w3.eth.contract(address=contract_address, abi=abi)
            
            # Gọi hàm addIssuer trên Smart Contract (quyền này vừa phát hành vừa thu hồi được)
            tx_data = contract.functions.addIssuer(wallet)._encode_transaction_data()
            
            context = {
                'action_name': 'CẤP QUYỀN PHÁT HÀNH VÀ THU HỒI',
                'target_wallet': wallet,
                'target_user': user_to_authorize.username,
                'contract_address': contract_address,
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