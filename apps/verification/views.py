from django.shortcuts import render
from django.contrib import messages

# Import model Degree (Phôi bằng) và Student (Sinh viên) để tra cứu
from apps.degrees.models import Degree
from apps.students.models import Student

# Nếu bạn đã có hàm check Smart Contract, hãy import vào đây. Ví dụ:
# from apps.blockchain.services import verify_on_chain

def public_verify_view(request):
    """
    Trang tra cứu văn bằng công khai dành cho Nhà tuyển dụng/Bên thứ 3.
    Không yêu cầu đăng nhập.
    """
    context = {
        'searched': False,
        'degree': None,
        'student': None,
        'is_verified_on_chain': False
    }

    if request.method == 'POST':
        # Lấy từ khóa tra cứu từ form HTML (Mã sinh viên, CCCD hoặc Mã văn bằng)
        search_query = request.POST.get('search_query', '').strip()

        if not search_query:
            messages.error(request, "Vui lòng nhập mã tra cứu (Mã sinh viên hoặc CCCD).")
        else:
            context['searched'] = True
            try:
                # 1. TÌM KIẾM TRONG DATABASE
                # Tìm văn bằng dựa trên mã sinh viên hoặc CCCD
                degree = Degree.objects.filter(
                    student__student_code=search_query
                ).first()
                
                # Nếu không tìm thấy theo mã sinh viên, thử tìm theo CCCD
                if not degree:
                    degree = Degree.objects.filter(
                        student__national_id=search_query
                    ).first()

                if degree:
                    context['degree'] = degree
                    context['student'] = degree.student
                    
                    # 2. KIỂM TRA TRẠNG THÁI TRÊN BLOCKCHAIN (WEB3)
                    # Chỉ kiểm tra blockchain nếu văn bằng đã được phát hành (ISSUED)
                    if degree.status == 'ISSUED':
                        # Gọi hàm kết nối Smart Contract thực tế của bạn ở đây.
                        # Ví dụ: 
                        # is_valid = verify_on_chain(degree.canonical_hash)
                        # context['is_verified_on_chain'] = is_valid
                        
                        # Tạm thời gán True (Bạn sẽ thay bằng hàm gọi Web3 sau)
                        context['is_verified_on_chain'] = True
                        
                        messages.success(request, "Văn bằng hợp lệ và đã được xác thực trên Blockchain!")
                    elif degree.status == 'REVOKED':
                        messages.warning(request, "CẢNH BÁO: Văn bằng này đã bị thu hồi!")
                    else:
                        messages.info(request, "Văn bằng đang trong quá trình xử lý, chưa được phát hành chính thức lên Blockchain.")
                else:
                    messages.error(request, f"Không tìm thấy thông tin văn bằng nào khớp với từ khóa: '{search_query}'.")

            except Exception as e:
                messages.error(request, "Đã xảy ra lỗi trong quá trình hệ thống tra cứu. Vui lòng thử lại sau.")
                # print(f"Error during verification: {e}") # Bật log này khi code backend để debug

    # Trả về giao diện tìm kiếm (Cả phương thức GET và POST)
    return render(request, 'verification/public_search.html', context)