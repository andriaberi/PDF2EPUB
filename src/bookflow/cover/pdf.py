import pymupdf

from .image import to_cover
from .models import Cover

# The first page is a cover when a picture fills most of it and there is almost no
# text: a scanned cover has a few words of OCR noise, a title page has sentences.
MIN_IMAGE_SHARE = 0.6
MAX_WORDS = 20

# Height of the rendered cover in pixels, sharp enough for any reader.
COVER_HEIGHT = 1600


def find_cover(path: str) -> Cover | None:
    """The PDF's own cover: its first page, when that page is a picture."""
    with pymupdf.open(path) as doc:
        if not doc.page_count:
            return None
        page = doc[0]
        if not is_cover(page):
            return None
        zoom = COVER_HEIGHT / page.rect.height
        return to_cover(page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False))


def is_cover(page: pymupdf.Page) -> bool:
    area = page.rect.width * page.rect.height
    if not area:
        return False
    images = page.get_image_info()
    largest = max((pymupdf.Rect(image["bbox"]).get_area() for image in images), default=0)
    return largest / area >= MIN_IMAGE_SHARE and len(page.get_text("words")) <= MAX_WORDS
