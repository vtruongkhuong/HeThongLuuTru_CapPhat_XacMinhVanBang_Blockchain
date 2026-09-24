from django.contrib import admin
from apps.core.admin import BaseRoleAdmin

from .models import Faculty, Major, DegreeType

# Cấp quyền cho nhóm Cán bộ nhập liệu / Cán bộ đào tạo
ALLOWED_ACADEMIC_ROLES = ['officer_a', 'academic_staff']


@admin.register(Faculty)
class FacultyAdmin(BaseRoleAdmin):
    allowed_roles = ALLOWED_ACADEMIC_ROLES
    list_display = ('code', 'name', 'is_active')
    search_fields = ('code', 'name')
    list_filter = ('is_active',)
    list_filter_submit = True


@admin.register(Major)
class MajorAdmin(BaseRoleAdmin):
    allowed_roles = ALLOWED_ACADEMIC_ROLES
    list_display = ('code', 'name', 'faculty', 'is_active')
    search_fields = ('code', 'name')
    list_filter = ('faculty', 'is_active')
    list_filter_submit = True
    autocomplete_fields = ['faculty']


@admin.register(DegreeType)
class DegreeTypeAdmin(BaseRoleAdmin):
    allowed_roles = ALLOWED_ACADEMIC_ROLES
    list_display = ('code', 'name', 'template_name', 'is_active')
    search_fields = ('code', 'name')
    list_filter = ('is_active',)