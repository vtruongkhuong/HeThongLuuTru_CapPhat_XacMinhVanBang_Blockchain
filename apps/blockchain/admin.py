from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path
from apps.degrees.models import Degree
from apps.core.admin import BaseRoleAdmin
from apps.workflow.services import transition
from .models import IssuanceBatch, BlockchainTransaction
from .client import BlockchainClient
from .tasks import sync_transaction
import web3
import json
import os

@admin.register(IssuanceBatch)
class IssuanceBatchAdmin(BaseRoleAdmin):
    # CHỈ role issuer (Người phát hành) mới được vào đây
    allowed_roles = ['issuer']
    
    list_display = ['graduation_batch', 'merkle_root', 'status', 'created_at']
    actions = ['issue_with_metamask']

    # --- ACTION 1: HIỂN THỊ MÀN HÌNH KÝ ---
    @admin.action(description="Phát hành bằng MetaMask (Non-custodial)")
    def issue_with_metamask(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Chỉ được chọn 1 đợt để phát hành mỗi lần!", level=messages.ERROR)
            return
        
        batch = queryset.first()
        if batch.status == 'CONFIRMED':
            self.message_user(request, "Đợt này đã phát hành và xác nhận trên Blockchain rồi!", level=messages.ERROR)
            return
            
        try:
            client = BlockchainClient()
            contract_address = client.contract_address
            # Chống phát hành trùng: kiểm tra trên chain xem batchId đã có root chưa
            batch_id_hex = client.batch_id_of(batch.graduation_batch.name)
            existing_batch = client.get_batch(batch_id_hex)
            if existing_batch and existing_batch['root'] not in ('', '0' * 64):
                self.message_user(
                    request,
                    f"Cảnh báo: Đợt '{batch.graduation_batch.name}' đã được lưu trên Blockchain (batchId: {batch_id_hex[:10]}...)!",
                    level=messages.WARNING
                )
                return
            # Đếm số lượng văn bằng thực tế trong đợt
            count = Degree.objects.filter(batch=batch.graduation_batch).count()
            if count == 0:
                self.message_user(request, "Đợt tốt nghiệp này chưa có văn bằng nào được tạo!", level=messages.ERROR)
                return
            
             # Sinh dữ liệu giao dịch storeBatch(batchName, merkleRoot, count)
            tx_data = client.build_issue_tx_data(
                batch.graduation_batch.name,
                batch.merkle_root,
                count
            )
            context = {
                'batch': batch,
                'contract_address': contract_address,
                'tx_data': tx_data,
            }
            return render(request, 'admin/blockchain/issuancebatch/issue_metamask.html', context)
            
        except Exception as e:
            self.message_user(request, f"Lỗi khởi tạo giao dịch Web3: {str(e)}", level=messages.ERROR)

    # --- KHAI BÁO THÊM URL ẨN ĐỂ NHẬN TX_HASH ---
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('save-tx-hash/', self.admin_site.admin_view(self.save_tx_hash), name='blockchain_issuancebatch_save_tx_hash'),
        ]
        return custom_urls + urls


    # --- HÀM XỬ LÝ NHẬN TX HASH TỪ METAMASK GỬI VỀ ---
    def save_tx_hash(self, request):
        if request.method == 'POST':
            tx_hash = request.POST.get('tx_hash')
            batch_id = request.POST.get('batch_id')
            
            try:
                batch = IssuanceBatch.objects.get(id=batch_id)
            except IssuanceBatch.DoesNotExist:
                self.message_user(request, "Không tìm thấy đợt phát hành tương ứng!", level=messages.ERROR)
                return redirect('admin:blockchain_issuancebatch_changelist')
            # 1. Tạo bản ghi giao dịch BlockchainTransaction với trạng thái 'pending'
            BlockchainTransaction.objects.update_or_create(
                tx_hash=tx_hash,
                defaults={
                    'issuance_batch': batch,
                    'operation_type': 'ISSUE',
                    'status': 'pending'
                }
            )
            # Cập nhật tx_hash vào GraduationBatch để tiện tra cứu
            batch.graduation_batch.tx_hash = tx_hash
            batch.graduation_batch.save(update_fields=['tx_hash'])
            # 2. TỐI ƯU: Cập nhật hàng loạt trạng thái Degree sang ISSUANCE_PENDING chỉ trong 1 câu lệnh SQL duy nhất
            Degree.objects.filter(
                batch=batch.graduation_batch,
                status__in=('APPROVED', 'DRAFT', 'GENERATED')
            ).update(status='ISSUANCE_PENDING')
            # 3. Kích hoạt Celery task đồng bộ giao dịch
            try:
                sync_transaction.delay(tx_hash)
            except Exception:
                pass
            self.message_user(
                request,
                f"Đã gửi giao dịch phát hành ({tx_hash[:10]}...{tx_hash[-8:]})! "
                f"Hệ thống đang theo dõi xác nhận trên mạng Sepolia.",
                level=messages.SUCCESS
            )
            return redirect('admin:blockchain_issuancebatch_changelist')