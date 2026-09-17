class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Code xử lý của bạn
        response = self.get_response(request)
        return response