import time
from django.core.cache import cache

RATE_LIMIT_REQUESTS = 15  # Tối đa 15 lượt tra cứu
RATE_LIMIT_WINDOW = 60    # Trong vòng 60 giây mỗi IP


def get_client_ip(request):
    """Lấy địa chỉ IP thực của người tra cứu"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '127.0.0.1')


def check_verification_throttle(request):
    """
    Kiểm tra giới hạn tần suất tra cứu.
    Trả về tuple: (is_allowed: bool, retry_after_seconds: int)
    """
    ip = get_client_ip(request)
    cache_key = f"verify_throttle_{ip}"
    now = time.time()

    history = cache.get(cache_key, [])
    # Giữ lại các request trong khung thời gian 60s gần nhất
    history = [ts for ts in history if now - ts < RATE_LIMIT_WINDOW]

    if len(history) >= RATE_LIMIT_REQUESTS:
        retry_after = int(RATE_LIMIT_WINDOW - (now - history[0])) + 1
        return False, max(retry_after, 1)

    history.append(now)
    cache.set(cache_key, history, timeout=RATE_LIMIT_WINDOW)
    return True, 0