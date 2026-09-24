from django.contrib import admin
from apps.core.admin import BaseRoleAdmin

# TODO: Thay BlockchainTransaction bằng tên model thực tế của bạn trong apps/blockchain/models.py
from .models import BlockchainTransaction


@admin.register(BlockchainTransaction)
class BlockchainTransactionAdmin(BaseRoleAdmin):
    # CHỈ tác nhân Người phát hành Web3 (Authorized Issuer) mới được xem và thao tác ở module này
    allowed_roles = ['issuer']

    # TODO: Thay đổi các field dưới đây cho khớp với cột trong model của bạn
    list_display = ('id', 'tx_hash', 'status', 'created_at')
    search_fields = ('tx_hash',)
    list_filter = ('status',)
    
    # Có thể thêm các @admin.action ở đây để xử lý logic ký giao dịch với Smart Contract