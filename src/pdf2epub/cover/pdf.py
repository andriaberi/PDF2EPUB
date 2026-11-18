import pymupdf

from .image import to_cover
from .models import Cover

MIN_IMAGE_SHARE = 0.6
MAX_WORDS = 20
COVER_HEIGHT = 1600


def find_cover(path: str) -> Cover | None:
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
