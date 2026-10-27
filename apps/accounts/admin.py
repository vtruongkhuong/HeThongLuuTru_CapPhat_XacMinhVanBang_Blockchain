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

    # Danh sách các thao tác phân quyền Blockchain trực tiếp qua MetaMask (Không cần vào Remix)
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

    # --- HELPER DÙNG CHUNG CHO MỌI THAO TÁC PHÂN QUYỀN BLOCKCHAIN ---
    def _render_blockchain_action(self, request, queryset, function_name, action_label):
        if queryset.count() != 1:
            self.message_user(request, "Vui lòng chỉ chọn đúng 1 tài khoản mỗi lần thao tác phân quyền.", level=messages.ERROR)
            return

        user_to_authorize = queryset.first()
        wallet = user_to_authorize.wallet_address

        if not wallet or not wallet.startswith('0x') or len(wallet) != 42:
            self.message_user(
                request,
                f"Tài khoản '{user_to_authorize.username}' chưa có địa chỉ ví MetaMask hợp lệ (dạng 0x... 42 ký tự)!",
                level=messages.ERROR
            )
            return

        try:
            client = BlockchainClient()
            contract = client.contract
            fn = getattr(contract.functions, function_name, None)
            if not fn:
                self.message_user(request, f"Hàm {function_name} chưa tồn tại trên Smart Contract ABI!", level=messages.ERROR)
                return

            checksum_wallet = client.w3.to_checksum_address(wallet)
            tx_data = fn(checksum_wallet)._encode_transaction_data()

            context = {
                'action_name': action_label,
                'target_wallet': checksum_wallet,
                'target_user': user_to_authorize.username,
                'contract_address': client.contract_address,
                'tx_data': tx_data,
            }
            return render(request, 'admin/accounts/authorize_metamask.html', context)

        except Exception as e:
            self.message_user(request, f"Lỗi khởi tạo giao dịch Web3: {str(e)}", level=messages.ERROR)

    # 1. Cấp quyền Quản trị viên (Admin)
    @admin.action(description="👑 1. Cấp quyền QUẢN TRỊ VIÊN (ADMIN) trên Blockchain")
    def add_admin_on_blockchain(self, request, queryset):
        return self._render_blockchain_action(
            request, queryset, 'addAdmin', 'CẤP QUYỀN QUẢN TRỊ VIÊN (ADMIN)'
        )

    # 2. Thu hồi quyền Quản trị viên (Admin)
    @admin.action(description="🚫 2. Thu hồi quyền QUẢN TRỊ VIÊN (ADMIN) trên Blockchain")
    def remove_admin_on_blockchain(self, request, queryset):
        return self._render_blockchain_action(
            request, queryset, 'removeAdmin', 'THU HỒI QUYỀN QUẢN TRỊ VIÊN (ADMIN)'
        )

    # 3. Cấp quyền Cán bộ (Issuer)
    @admin.action(description="⚡ 3. Cấp quyền CÁN BỘ PHÁT HÀNH & THU HỒI (Issuer)")
    def authorize_issuer_on_blockchain(self, request, queryset):
        return self._render_blockchain_action(
            request, queryset, 'addIssuer', 'CẤP QUYỀN CÁN BỘ PHÁT HÀNH & THU HỒI'
        )

    # 4. Tạm khóa quyền Cán bộ
    @admin.action(description="⏸️ 4. Tạm khóa quyền Cán bộ (Pause Issuer)")
    def pause_issuer_on_blockchain(self, request, queryset):
        return self._render_blockchain_action(
            request, queryset, 'pauseIssuer', 'TẠM KHÓA QUYỀN CÁN BỘ (PAUSE)'
        )

    # 5. Mở khóa quyền Cán bộ
    @admin.action(description="▶️ 5. Mở khóa quyền Cán bộ (Unpause Issuer)")
    def unpause_issuer_on_blockchain(self, request, queryset):
        return self._render_blockchain_action(
            request, queryset, 'unpauseIssuer', 'MỞ KHÓA QUYỀN CÁN BỘ (UNPAUSE)'
        )

    # 6. Thu hồi vĩnh viễn quyền Cán bộ
    @admin.action(description="❌ 6. Thu hồi vĩnh viễn quyền Cán bộ (Remove Issuer)")
    def remove_issuer_on_blockchain(self, request, queryset):
        return self._render_blockchain_action(
            request, queryset, 'removeIssuer', 'THU HỒI VĨNH VIỄN QUYỀN CÁN BỘ'
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
