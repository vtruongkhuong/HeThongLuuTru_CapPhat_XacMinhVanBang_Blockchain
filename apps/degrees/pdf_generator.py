import os
from io import BytesIO
from django.template.loader import get_template
from xhtml2pdf import pisa

def get_degree_pdf(degree):
    """
    Tạo file PDF từ object Degree bằng xhtml2pdf.
    Hàm này được dùng chung cho Admin xem trước và Sinh viên tải về.
    """
    # Trỏ tới file giao diện HTML của phôi bằng
    template = get_template('degrees/pdf/degree_template.html')
    
    # Truyền dữ liệu thật vào HTML
    context = {
        'degree': degree,
        'student': degree.student,
    }
    html = template.render(context)
    result = BytesIO()
    
    # Render ra PDF
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    
    if not pdf.err:
        return result.getvalue()
    return None