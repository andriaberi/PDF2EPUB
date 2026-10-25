from pathlib import Path

import pymupdf

from .models import Cover, CoverError

JPEG_QUALITY = 90


def load_cover(image: str | bytes) -> Cover:
    """Read a cover image from a file or its bytes: JPEG, PNG and most other formats."""
    if isinstance(image, str) and not Path(image).is_file():
        raise CoverError(f"no such cover image: {image}")
    try:
        pixmap = pymupdf.Pixmap(image)
    except (pymupdf.mupdf.FzErrorBase, pymupdf.FileDataError, RuntimeError, ValueError):
        name = image if isinstance(image, str) else "the given cover"
        raise CoverError(f"not an image: {name}") from None
    return to_cover(pixmap)


def to_cover(pixmap: pymupdf.Pixmap) -> Cover:
    if pixmap.alpha:
        pixmap = pymupdf.Pixmap(pixmap, 0)
    if pixmap.colorspace is None or pixmap.colorspace.n != 3:
        pixmap = pymupdf.Pixmap(pymupdf.csRGB, pixmap)
    return Cover(pixmap.tobytes("jpeg", jpg_quality=JPEG_QUALITY), pixmap.width, pixmap.height)
