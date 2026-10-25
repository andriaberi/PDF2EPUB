from pathlib import Path

import pymupdf

from .reader import ReadError

# Wide enough for any screen; wider would only take memory.
MAX_WIDTH = 3000


def render_page(path: str, number: int, width: int = 800) -> bytes:
    """Page `number` of the PDF, from 1 as blocks give it, as a PNG image `width` wide."""
    if not 1 <= width <= MAX_WIDTH:
        raise ReadError(f"a page can be shown 1 to {MAX_WIDTH} pixels wide, not {width}")
    if not Path(path).is_file():
        raise ReadError(f"no such file: {path}")
    try:
        doc = pymupdf.open(path)
    except (pymupdf.FileDataError, RuntimeError) as e:
        raise ReadError(f"not a readable PDF: {path} ({e})") from None
    with doc:
        if not 1 <= number <= doc.page_count:
            raise ReadError(f"no page {number}: the PDF has {doc.page_count}")
        page = doc[number - 1]
        zoom = width / page.rect.width
        return bytes(page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).tobytes("png"))
