from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from django.contrib import admin
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

    list_display = ('username', 'email', 'employee_code', 'department', 'display_status')
    list_filter = ('is_active', 'is_locked', 'department')
    search_fields = ('username', 'email', 'employee_code')
    inlines = [UserRoleInline]

    fieldsets = DjangoUserAdmin.fieldsets + (
        ('Thông tin nghiệp vụ', {
            'fields': ('employee_code', 'phone_number', 'department', 'is_locked')
        }),
    )

    @display(description="Trạng thái", label={"Hoạt động": "success", "Khóa": "danger"})
    def display_status(self, obj):
        return "Khóa" if obj.is_locked or not obj.is_active else "Hoạt động"


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
