import uuid

class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Khởi tạo Request ID duy nhất cho phiên làm việc
        request.request_id = str(uuid.uuid4())
        
        # 2. Bắt IP của máy trạm thực hiện request
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        request.client_ip = ip

        response = self.get_response(request)
        return response