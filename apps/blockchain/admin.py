from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path
from django.conf import settings
from apps.core.admin import BaseRoleAdmin
from .models import IssuanceBatch, BlockchainTransaction
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
        if batch.status != 'PENDING':
            self.message_user(request, "Đợt này đã phát hành rồi hoặc không hợp lệ!", level=messages.ERROR)
            return
            
        try:
            # 1. Khởi tạo Web3 và nạp Contract
            w3 = web3.Web3()
            contract_address = settings.CONTRACT_ADDRESS
            abi_path = os.path.join(settings.BASE_DIR, 'apps', 'blockchain', 'contracts_abi', 'DegreeVerification.json')
            
            with open(abi_path, 'r') as f:
                abi = json.load(f)
            contract = w3.eth.contract(address=contract_address, abi=abi)
            
            # 2. Sinh dữ liệu giao dịch chưa ký (chỉ mã hóa dữ liệu, KHÔNG CẦN PRIVATE KEY)
            # Hàm trên Smart Contract là: storeMerkleRoot(string _batchName, string _merkleRoot)
            tx_data = contract.functions.storeMerkleRoot(
                batch.graduation_batch.name, 
                batch.merkle_root
            )._encode_transaction_data()

            # 3. Ném dữ liệu ra HTML để Frontend xử lý
            context = {
                'batch': batch,
                'contract_address': contract_address,
                'tx_data': tx_data,
            }
            return render(request, 'admin/blockchain/issuancebatch/issue_metamask.html', context)
            
        except Exception as e:
            self.message_user(request, f"Lỗi hệ thống Web3: {str(e)}", level=messages.ERROR)

    # --- KHAI BÁO THÊM URL ẨN ĐỂ NHẬN TX_HASH ---
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('save-tx-hash/', self.admin_site.admin_view(self.save_tx_hash), name='blockchain_issuancebatch_save_tx_hash'),
        ]
        return custom_urls + urls

    # --- HÀM XỬ LÝ NHẬN TX HASH TỪ GIAO DIỆN TRẢ VỀ ---
    def save_tx_hash(self, request):
        if request.method == 'POST':
            tx_hash = request.POST.get('tx_hash')
            batch_id = request.POST.get('batch_id')
            
            # Cập nhật trạng thái đợt
            batch = IssuanceBatch.objects.get(id=batch_id)
            batch.status = 'PROCESSING' # Chuyển sang đang xử lý chờ mạng lưới xác nhận
            batch.save()
            
            # Lưu biên lai giao dịch
            BlockchainTransaction.objects.create(
                issuance_batch=batch,
                tx_hash=tx_hash,
                status='PENDING' # Task chạy ngầm sẽ kiểm tra trạng thái này sau
            )
            
            self.message_user(request, f"Đã đẩy lên mạng Sepolia thành công! Tx Hash: {tx_hash}", level=messages.SUCCESS)
            return redirect('admin:blockchain_issuancebatch_changelist')