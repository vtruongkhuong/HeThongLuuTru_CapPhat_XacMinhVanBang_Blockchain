from django.core.exceptions import ValidationError

def ensure_different_actors(*users):
    """
    Kiểm tra quy tắc 4-eyes (hoặc n-eyes): Đảm bảo các tác nhân thực hiện
    các bước trong một quy trình là những người hoàn toàn khác nhau.
    
    Args:
        *users: Danh sách các đối tượng User truyền vào (có thể chứa None nếu bước đó chưa xảy ra).
        
    Raises:
        ValidationError: Nếu phát hiện một người thực hiện nhiều hơn một bước.
    """
    
    # 1. Lọc bỏ các giá trị None (những bước chưa có người thực hiện)
    active_users = [user for user in users if user is not None]
    
    # 2. Nếu chưa có ai thực hiện hoặc mới có 1 người thực hiện thì hợp lệ
    if len(active_users) <= 1:
        return True
        
    # 3. Lấy ra danh sách ID của những người đã thực hiện
    user_ids = [user.id for user in active_users]
    
    # 4. Dùng set() để loại bỏ các ID trùng lặp. 
    # Nếu số lượng ID sau khi lọc nhỏ hơn số lượng ID ban đầu => Có người trùng nhau!
    if len(user_ids) != len(set(user_ids)):
        raise ValidationError(
            "Lỗi bảo mật (Quy tắc 4-eyes): Một tài khoản không được phép "
            "thực hiện nhiều bước (Tạo/Duyệt/Thực thi) trong cùng một quy trình!"
        )
        
    return True