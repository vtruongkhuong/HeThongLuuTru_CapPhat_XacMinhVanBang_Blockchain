from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import GraduationBatch

@admin.register(GraduationBatch)
class GraduationBatchAdmin(ModelAdmin):
    list_display = ['name']
    search_fields = ['name']