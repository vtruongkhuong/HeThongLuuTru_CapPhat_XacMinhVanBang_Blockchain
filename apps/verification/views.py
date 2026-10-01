from django.shortcuts import render
from django.contrib import messages

# Import model Degree (Phôi bằng) và Student (Sinh viên) để tra cứu
from apps.degrees.models import Degree
from apps.students.models import Student
from .models import VerificationLog
# Nếu bạn đã có hàm check Smart Contract, hãy import vào đây. Ví dụ:
# from apps.blockchain.services import verify_on_chain
def landing_view(request):
    return render(request, 'verification/landing.html')
def public_verify_view(request):
    context = {
        'searched': False,
        'degree': None,
        'student': None,
        'is_verified_on_chain': False
    }

    if request.method == 'POST':
        # 1. NHẬN MÃ: Lấy chuỗi từ Form nhập tay hoặc từ QR Code bắn qua
        search_query = request.POST.get('search_query', '').strip()

        if search_query:
            context['searched'] = True
            
            # 2. TRUY VẤN DB: Check xem mã SV hoặc CCCD có tồn tại không
            degree = Degree.objects.filter(student__student_code=search_query).first()
            if not degree:
                degree = Degree.objects.filter(student__national_id=search_query).first()

            # 3. GHI LOG: Lưu lại lịch sử tra cứu của Nhà tuyển dụng
            # Lấy IP của người tra cứu
            client_ip = request.META.get('REMOTE_ADDR')
            # Lấy thông tin trình duyệt
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            VerificationLog.objects.create(
                search_query=search_query,
                degree=degree, # Nếu tìm thấy thì lưu id văn bằng, không thì Null
                ip_address=client_ip,
                user_agent=user_agent,
                is_successful=bool(degree)
            )

            # 4. TRẢ KẾT QUẢ VÀ KIỂM TRA THU HỒI
            if degree:
                context['degree'] = degree
                context['student'] = degree.student
                context['is_verified_on_chain'] = True # Tạm gán True chờ Khương ghép Web3
                
                if degree.status == 'REVOKED':
                    messages.warning(request, "Cảnh báo: Văn bằng này đã bị thu hồi!")
                elif degree.status == 'ISSUED':
                    messages.success(request, "Văn bằng hợp lệ và tồn tại trên hệ thống!")
            else:
                messages.error(request, f"Không tìm thấy dữ liệu cho mã: {search_query}")
        else:
            messages.error(request, "Vui lòng nhập hoặc quét mã để tra cứu.")

    return render(request, 'verification/public_search.html', context)
def verify_temp_cert_view(request):
    """
    Trang tra cứu Giấy chứng nhận tốt nghiệp tạm thời
    """
    return render(request, 'verification/verify_temp_cert.html')    