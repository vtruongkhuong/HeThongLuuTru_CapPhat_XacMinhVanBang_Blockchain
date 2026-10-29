from apps.core.admin import format_crypto_hash_badge
from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html
from django.core.exceptions import ValidationError

from apps.degrees.models import Degree
from .models import ReasonCode, RevocationRequest
from . import services

try:
    from apps.core.admin import BaseRoleAdmin
except ImportError:
    try:
        from unfold.admin import ModelAdmin as BaseRoleAdmin
    except ImportError:
        BaseRoleAdmin = admin.ModelAdmin


def _user_has_role(user, role_names):
    """Kiểm tra user có thuộc role/group được chỉ định không"""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    user_role = getattr(user, 'role', None)
    if user_role in role_names:
        return True
    return user.groups.filter(name__in=role_names).exists()


@admin.register(ReasonCode)
class ReasonCodeAdmin(BaseRoleAdmin):
    list_display = ('code', 'description')
    search_fields = ('code', 'description')

    def has_module_permission(self, request):
        return _user_has_role(request.user, ['officer_a', 'officer_b', 'issuer', 'super_admin'])

    def has_view_permission(self, request, obj=None):
        return _user_has_role(request.user, ['officer_a', 'officer_b', 'issuer', 'super_admin'])

    def has_add_permission(self, request):
        return _user_has_role(request.user, ['officer_a', 'super_admin'])

    def has_change_permission(self, request, obj=None):
        return _user_has_role(request.user, ['officer_a', 'super_admin'])


@admin.register(RevocationRequest)
class RevocationRequestAdmin(BaseRoleAdmin):
    list_display = (
        'id',
        'degree',
        'reason_code',
        'status',
        'requested_by',
        'approved_by',
        'executed_by',
        'metamask_action_link',
    )
    list_filter = ('status', 'reason_code')
    list_filter_submit = True
    search_fields = ('degree__student__student_code', 'degree__student__full_name', 'tx_hash')
    readonly_fields = (
        'requested_by',
        'requested_at',
        'approved_by',
        'approved_at',
        'executed_by',
        'executed_at',
        'status',
        'tx_hash',
    )
    actions = ['action_approve_revocation', 'action_reject_revocation', 'action_execute_revocation']

    # --- CẤU HÌNH QUYỀN TRUY CẬP MODULE THEO ROLE ---
    def has_module_permission(self, request):
        return _user_has_role(request.user, ['officer_a', 'officer_b', 'approver', 'issuer', 'super_admin'])

    def has_view_permission(self, request, obj=None):
        return _user_has_role(request.user, ['officer_a', 'officer_b', 'approver', 'issuer', 'super_admin'])

    def has_add_permission(self, request):
        # Chỉ Officer A (hoặc Super Admin) mới được tạo yêu cầu thu hồi mới
        return _user_has_role(request.user, ['officer_a', 'super_admin'])

    def has_change_permission(self, request, obj=None):
        # Cho phép Officer B và Issuer tích chọn checkbox trên bảng để chạy Action
        if obj is None:
            return _user_has_role(request.user, ['officer_a', 'officer_b', 'approver', 'issuer', 'super_admin'])
        return _user_has_role(request.user, ['super_admin'])

    def has_delete_permission(self, request, obj=None):
        return _user_has_role(request.user, ['super_admin'])

    def get_actions(self, request):
        """Ẩn/hiện các Action trong menu thả xuống đúng theo từng Role"""
        actions = super().get_actions(request)
        if request.user.is_superuser:
            return actions

        if not _user_has_role(request.user, ['officer_b', 'approver']):
            actions.pop('action_approve_revocation', None)
            actions.pop('action_reject_revocation', None)

        if not _user_has_role(request.user, ['issuer']):
            actions.pop('action_execute_revocation', None)

        return actions

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Chỉ hiển thị các văn bằng đang ở trạng thái ISSUED trong danh sách chọn"""
        if db_field.name == "degree":
            existing_revocation_degree_ids = RevocationRequest.objects.filter(
                status__in=['PENDING', 'APPROVED', 'EXECUTED']
            ).values_list('degree_id', flat=True)

            object_id = request.resolver_match.kwargs.get('object_id')
            if object_id:
                existing_revocation_degree_ids = existing_revocation_degree_ids.exclude(pk=object_id)
                current_req = RevocationRequest.objects.filter(pk=object_id).first()
                if current_req:
                    kwargs["queryset"] = Degree.objects.filter(pk=current_req.degree_id)
                else:
                    kwargs["queryset"] = Degree.objects.filter(status='ISSUED')
            else:
                kwargs["queryset"] = Degree.objects.filter(status='ISSUED').exclude(
                    pk__in=existing_revocation_degree_ids
                )
        elif db_field.name == "supersedes":
            kwargs["queryset"] = Degree.objects.exclude(status='REVOKED')

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def metamask_action_link(self, obj):
        if obj.status == 'APPROVED':
            url = reverse('revocation:execute_metamask', args=[obj.pk])
            return format_html(
                '<a href="{}" class="apple-action-btn-primary">'
                '<span class="material-symbols-outlined" style="font-size:14px;">vpn_key</span>'
                '<span>Ký MetaMask (Thực thi)</span>'
                '</a>',
                url
            )
        elif obj.status == 'EXECUTED' and obj.tx_hash:
            return format_crypto_hash_badge(obj.tx_hash, title_prefix='Mã TxHash Thu Hồi', icon='link')
        return "-"
    metamask_action_link.short_description = "Thực thi On-Chain"

    def save_model(self, request, obj, form, change):
        if not change:
            if not _user_has_role(request.user, ['officer_a', 'super_admin']):
                messages.error(request, "Chỉ cán bộ tạo yêu cầu (officer_a) mới có quyền khởi tạo yêu cầu thu hồi.")
                return
            try:
                services.validate_degree_can_be_revoked(obj.degree)
            except ValidationError as e:
                err_msg = e.messages[0] if hasattr(e, 'messages') else str(e)
                messages.error(request, err_msg)
                return
            obj.requested_by = request.user
            obj.status = 'PENDING'
        super().save_model(request, obj, form, change)

    @admin.action(description="1. Duyệt thu hồi (Dành cho Officer B)")
    def action_approve_revocation(self, request, queryset):
        if not _user_has_role(request.user, ['officer_b', 'approver', 'super_admin']):
            self.message_user(request, "Bạn không có quyền Officer B để duyệt yêu cầu thu hồi.", level=messages.ERROR)
            return

        success_count = 0
        for rev_req in queryset:
            try:
                services.approve(revocation_request=rev_req, approved_by=request.user, http_request=request)
                success_count += 1
            except ValidationError as e:
                err_msg = e.messages[0] if hasattr(e, 'messages') else str(e)
                self.message_user(request, f"Yêu cầu #{rev_req.pk}: {err_msg}", level=messages.ERROR)

        if success_count:
            self.message_user(request, f"Đã phê duyệt thành công {success_count} yêu cầu thu hồi.", level=messages.SUCCESS)

    @admin.action(description="2. Từ chối thu hồi (Dành cho Officer B)")
    def action_reject_revocation(self, request, queryset):
        if not _user_has_role(request.user, ['officer_b', 'approver', 'super_admin']):
            self.message_user(request, "Bạn không có quyền Officer B để từ chối yêu cầu thu hồi.", level=messages.ERROR)
            return

        success_count = 0
        for rev_req in queryset:
            try:
                services.reject(revocation_request=rev_req, rejected_by=request.user, http_request=request)
                success_count += 1
            except ValidationError as e:
                err_msg = e.messages[0] if hasattr(e, 'messages') else str(e)
                self.message_user(request, f"Yêu cầu #{rev_req.pk}: {err_msg}", level=messages.ERROR)

        if success_count:
            self.message_user(request, f"Đã từ chối {success_count} yêu cầu thu hồi.", level=messages.WARNING)

    @admin.action(description="3. Thực thi thu hồi qua MetaMask (Dành cho Issuer)")
    def action_execute_revocation(self, request, queryset):
        if not _user_has_role(request.user, ['issuer', 'super_admin']):
            self.message_user(request, "Chỉ tài khoản Issuer mới có quyền thực thi thu hồi trên Blockchain.", level=messages.ERROR)
            return

        if queryset.count() != 1:
            self.message_user(
                request,
                "Vui lòng chọn đúng 1 yêu cầu thu hồi ở trạng thái APPROVED để mở trang ký MetaMask.",
                level=messages.WARNING
            )
            return

        rev_req = queryset.first()
        if rev_req.status != 'APPROVED':
            self.message_user(
                request,
                f"Yêu cầu #{rev_req.pk} chưa được duyệt (Trạng thái hiện tại: {rev_req.status}).",
                level=messages.ERROR
            )
            return

        try:
            from apps.workflow.services import ensure_different_actors
            ensure_different_actors(rev_req.requested_by, rev_req.approved_by, request.user)
        except ValidationError as e:
            err_msg = e.messages[0] if hasattr(e, 'messages') else str(e)
            self.message_user(request, err_msg, level=messages.ERROR)
            return

        return redirect(reverse('revocation:execute_metamask', args=[rev_req.pk]))