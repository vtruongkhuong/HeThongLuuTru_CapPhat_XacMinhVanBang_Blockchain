from unfold.admin import ModelAdmin

class BaseRoleAdmin(ModelAdmin):
    """Class base phân quyền dùng chung cho toàn dự án."""
    allowed_roles = []

    def _has_role(self, request):
        if request.user.is_superuser:
            return True
        user_roles = request.user.roles.values_list('code', flat=True)
        return any(role in user_roles for role in self.allowed_roles)

    def has_module_permission(self, request):
        return self._has_role(request)

    def has_view_permission(self, request, obj=None):
        return self._has_role(request)

    def has_add_permission(self, request):
        return self._has_role(request)
        
    def has_change_permission(self, request, obj=None):
        return self._has_role(request)
        
    def has_delete_permission(self, request, obj=None):
        return self._has_role(request)