from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.template.loader import get_template
from PIL import Image, ImageChops, ImageDraw, ImageOps
from xhtml2pdf import pisa

STATIC_DIR = Path(settings.BASE_DIR) / "static"
LOGO_PATH = STATIC_DIR / "img" / "logo_ctut.png"
BG_PATH = STATIC_DIR / "img" / "degree_bg.png"   # file tự sinh ra

# A4 ngang, ~200 dpi
W, H = 2339, 1654
RED = (150, 20, 25)
GOLD = (192, 155, 77)
CREAM = (253, 250, 241)


def _diamond(d, cx, cy, r, fill):
    d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=fill)


def build_background():
    """Vẽ ảnh nền phôi bằng: giấy kem + hoa văn + logo mờ + viền kép."""
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)
    cx, cy = W // 2, H // 2

    # Vòng tròn đồng tâm rất nhạt (kiểu hoa văn chống giả)
    for r in range(260, 700, 22):
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(238, 228, 200), width=2)

    # Logo làm watermark: chỉ lấy phần "mực", bỏ nền trắng, tô màu vàng nhạt
    if LOGO_PATH.is_file():
        logo = Image.open(LOGO_PATH).convert("RGBA")
        logo.thumbnail((900, 900))
        alpha = logo.split()[3]
        ink = ImageOps.invert(logo.convert("L"))
        mask = ImageChops.multiply(ink, alpha).point(lambda v: int(v * 0.28))
        tint = Image.new("RGB", logo.size, (160, 125, 60))
        img.paste(tint, ((W - logo.width) // 2, (H - logo.height) // 2), mask)

    # Viền: đỏ dày ngoài cùng -> dải chấm vàng -> vàng -> đỏ mảnh
    d.rectangle((50, 50, W - 50, H - 50), outline=RED, width=12)
    d.rectangle((100, 100, W - 100, H - 100), outline=GOLD, width=4)
    d.rectangle((112, 112, W - 112, H - 112), outline=RED, width=2)

    # Dải chấm tròn giữa viền đỏ và viền vàng
    m = 79
    for x in range(m, W - m + 1, 28):
        for y in (m, H - m):
            d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=GOLD)
    for y in range(m, H - m + 1, 28):
        for x in (m, W - m):
            d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=GOLD)

    # Thoi vàng ở 4 góc và giữa các cạnh
    for px, py in [(m, m), (W - m, m), (m, H - m), (W - m, H - m),
                   (cx, m), (cx, H - m), (m, cy), (W - m, cy)]:
        _diamond(d, px, py, 18, GOLD)

    # Cung trang trí ở 4 góc bên trong khung
    for r in (60, 90):
        d.arc((112 - r, 112 - r, 112 + r, 112 + r), 0, 90, fill=GOLD, width=3)
        d.arc((W - 112 - r, 112 - r, W - 112 + r, 112 + r), 90, 180, fill=GOLD, width=3)
        d.arc((W - 112 - r, H - 112 - r, W - 112 + r, H - 112 + r), 180, 270, fill=GOLD, width=3)
        d.arc((112 - r, H - 112 - r, 112 + r, H - 112 + r), 270, 360, fill=GOLD, width=3)

    img.save(BG_PATH, dpi=(200, 200))


def ensure_background():
    """Tự vẽ lại nền khi chưa có, hoặc khi logo / file này vừa được sửa."""
    newest = Path(__file__).stat().st_mtime
    if LOGO_PATH.is_file():
        newest = max(newest, LOGO_PATH.stat().st_mtime)
    if not BG_PATH.is_file() or BG_PATH.stat().st_mtime < newest:
        build_background()


def link_callback(uri, rel):
    """Đổi /static/... trong template thành file thật trên ổ đĩa."""
    if uri.startswith(settings.STATIC_URL):
        path = STATIC_DIR / uri[len(settings.STATIC_URL):]
        if path.is_file():
            return str(path)
    return uri


def get_degree_pdf(degree):
    ensure_background()

    template = get_template("degrees/pdf/degree_template.html")
    html = template.render({
        "degree": degree,
        "student": degree.student,
    })

    result = BytesIO()
    pdf = pisa.CreatePDF(html, dest=result, encoding="UTF-8",
                         link_callback=link_callback)
    return None if pdf.err else result.getvalue()