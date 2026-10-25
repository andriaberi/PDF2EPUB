import pymupdf

from .reader import ReadError, open_pdf

# Wide enough for any screen; wider would only take memory.
MAX_WIDTH = 3000


def render_page(path: str, number: int, width: int = 800) -> bytes:
    """Page `number` of the PDF, from 1 as blocks give it, as a PNG image `width` wide."""
    if not 1 <= width <= MAX_WIDTH:
        raise ReadError(f"a page can be shown 1 to {MAX_WIDTH} pixels wide, not {width}")
    with open_pdf(path) as doc:
        if not 1 <= number <= doc.page_count:
            raise ReadError(f"no page {number}: the PDF has {doc.page_count}")
        page = doc[number - 1]
        zoom = width / page.rect.width
        return bytes(page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).tobytes("png"))
