def notifications_context(request):
    """
    Context processor cung cấp số lượng thông báo chưa đọc và danh sách thông báo mới
    cho toàn bộ template giao diện (Navbar bell icon).
    """
    if hasattr(request, 'user') and request.user.is_authenticated:
        unread_count = request.user.notifications.filter(is_read=False).count()
        recent_notifications = request.user.notifications.all()[:5]
        return {
            'unread_notifications_count': unread_count,
            'recent_notifications': recent_notifications,
        }
    return {
        'unread_notifications_count': 0,
        'recent_notifications': [],
    }
