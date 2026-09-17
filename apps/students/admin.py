from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Student, ImportBatch, ImportBatchItem


@admin.register(Student)
class StudentAdmin(ModelAdmin):
    list_display = ('student_code', 'full_name', 'faculty', 'major', 'enrollment_year')
    list_filter = ('faculty', 'major', 'enrollment_year')
    list_filter_submit = True
    search_fields = ('student_code', 'full_name', 'national_id')
    autocomplete_fields = ['faculty', 'major']


@admin.register(ImportBatch)
class ImportBatchAdmin(ModelAdmin):
    list_display = ('id', 'file_name', 'batch', 'imported_by', 'mode', 'inserted', 'updated', 'errors', 'created_at')
    list_filter = ('mode',)
    list_filter_submit = True
    readonly_fields = ('inserted', 'updated', 'skipped', 'errors')


@admin.register(ImportBatchItem)
class ImportBatchItemAdmin(ModelAdmin):
    list_display = ('import_batch', 'row_number', 'student_code', 'action', 'error_message')
    list_filter = ('action',)
    list_filter_submit = True
    search_fields = ('student_code',)