from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Faculty, Major, DegreeType


@admin.register(Faculty)
class FacultyAdmin(ModelAdmin):
    list_display = ('code', 'name', 'is_active')
    search_fields = ('code', 'name')
    list_filter = ('is_active',)
    list_filter_submit = True


@admin.register(Major)
class MajorAdmin(ModelAdmin):
    list_display = ('code', 'name', 'faculty', 'is_active')
    search_fields = ('code', 'name')
    list_filter = ('faculty', 'is_active')
    list_filter_submit = True
    autocomplete_fields = ['faculty']


@admin.register(DegreeType)
class DegreeTypeAdmin(ModelAdmin):
    list_display = ('code', 'name', 'template_name', 'is_active')
    search_fields = ('code', 'name')
    list_filter = ('is_active',)
