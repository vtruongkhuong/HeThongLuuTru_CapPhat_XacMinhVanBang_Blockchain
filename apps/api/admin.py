import secrets
from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from .models import APIClient


@admin.register(APIClient)
class APIClientAdmin(ModelAdmin):
    list_display = ('name', 'api_key_masked', 'is_active', 'usage_today', 'quota_per_day', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'contact_email')
    readonly_fields = ('api_key', 'created_at', 'usage_today')
    actions = ['generate_new_key', 'revoke_key', 'reset_usage']

    def api_key_masked(self, obj):
        if obj.api_key:
            return format_html('<code>{}</code>', obj.api_key[:8] + '...' + obj.api_key[-4:])
        return '-'
    api_key_masked.short_description = 'API Key'

    @admin.action(description='🔑 Tạo API key mới')
    def generate_new_key(self, request, queryset):
        for client in queryset:
            client.api_key = secrets.token_hex(32)
            client.save(update_fields=['api_key'])
        self.message_user(request, f'Đã tạo key mới cho {queryset.count()} client.')

    @admin.action(description='🚫 Thu hồi API key')
    def revoke_key(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f'Đã thu hồi {queryset.count()} API key.')

    @admin.action(description='🔄 Reset usage_today về 0')
    def reset_usage(self, request, queryset):
        queryset.update(usage_today=0)
        self.message_user(request, f'Đã reset usage cho {queryset.count()} client.')

    def save_model(self, request, obj, form, change):
        if not obj.api_key:
            obj.api_key = secrets.token_hex(32)
        super().save_model(request, obj, form, change)