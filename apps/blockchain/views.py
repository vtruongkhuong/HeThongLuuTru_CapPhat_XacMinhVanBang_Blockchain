import os
from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import redirect
from apps.degrees.models import Degree


def ipfs_viewer_view(request, cid):
    """
    Trạm điều phối xem file IPFS:
    Nếu có file PDF cục bộ thì phục vụ trực tiếp để xem ngay lập tức mà không bị timeout,
    nếu không có thì chuyển hướng sang IPFS Gateway công cộng.
    """
    degree = Degree.objects.filter(ipfs_cid=cid).first()
    if degree and degree.pdf_path:
        media_root = getattr(settings, 'MEDIA_ROOT', os.path.join(settings.BASE_DIR, 'media'))
        full_path = os.path.join(media_root, degree.pdf_path)
        if os.path.exists(full_path):
            with open(full_path, 'rb') as f:
                pdf_data = f.read()
            response = HttpResponse(pdf_data, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="IPFS_{cid[:10]}_{degree.student.student_code}.pdf"'
            return response

    # Fallback chuyển hướng Gateway
    return redirect(f"https://ipfs.io/ipfs/{cid}")
