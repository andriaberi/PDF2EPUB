from pathlib import Path

import pymupdf

from .models import Cover, CoverError

JPEG_QUALITY = 90


def load_cover(path: str) -> Cover:
    """Read a cover image from a file: JPEG, PNG and most other image formats."""
    if not Path(path).is_file():
        raise CoverError(f"no such cover image: {path}")
    try:
        pixmap = pymupdf.Pixmap(path)
    except (pymupdf.mupdf.FzErrorBase, pymupdf.FileDataError, RuntimeError, ValueError):
        raise CoverError(f"not an image: {path}") from None
    return to_cover(pixmap)


def to_cover(pixmap: pymupdf.Pixmap) -> Cover:
    if pixmap.alpha:
        pixmap = pymupdf.Pixmap(pixmap, 0)
    if pixmap.colorspace is None or pixmap.colorspace.n != 3:
        pixmap = pymupdf.Pixmap(pymupdf.csRGB, pixmap)
    return Cover(pixmap.tobytes("jpeg", jpg_quality=JPEG_QUALITY), pixmap.width, pixmap.height)
