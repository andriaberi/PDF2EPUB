from collections import Counter
from typing import Any

import pymupdf

from pdf2epub.cover.image import to_cover
from pdf2epub.cover.pdf import is_cover

from .models import Line, Page, Picture

# A picture smaller than this share of the page is an ornament or a speck.
MIN_AREA = 0.03

# The same image on this many pages or more is a logo, a frame or a background.
MIN_REPEATS = 3

# Pieces of a picture closer than this, in points, are one picture: PDFs often cut
# one into strips.
TOUCHING = 2

# A picture with more lines of text on it than this is a background the text is
# printed over, or a scanned page: the text is the book's, the picture isn't.
MAX_LINES_ON = 5

# The longest side of a picture in pixels, sharp enough for any reader.
MAX_SIDE = 1600

# A box on the page, and the pixels per point of its sharpest image.
Box = tuple[pymupdf.Rect, float]


def read_pictures(pdf_pages: list[pymupdf.Page], pages: list[Page]) -> None:
    """Find the pictures printed on the pages, and take off the lines printed on them:
    a map's names, a picture's own lettering. A scanned book has none, each of its
    pages being one."""
    if 2 * sum(page.scanned for page in pages) > len(pages):
        return
    images = [
        [i for i in pdf_page.get_image_info(hashes=True) if i["width"] and size(i).width > 0]
        for pdf_page in pdf_pages
    ]
    repeated = repeated_images(images)
    for pdf_page, page, found in zip(pdf_pages, pages, images, strict=True):
        # The cover is the book's cover already.
        if pdf_page.number == 0 and is_cover(pdf_page):
            continue
        boxes = [
            (size(image) & pdf_page.rect, image["width"] / size(image).width)
            for image in found
            if image["digest"] not in repeated
        ]
        for box, sharpness in joined(boxes):
            if box.is_empty or abs(box) < MIN_AREA * abs(pdf_page.rect):
                continue
            on = [line for line in page.lines if is_on(line, box)]
            if len(on) > MAX_LINES_ON:
                continue
            page.lines = [line for line in page.lines if not is_on(line, box)]
            page.pictures.append(render(pdf_page, box, sharpness))
        page.pictures.sort(key=lambda picture: picture.y0)


def size(image: dict[str, Any]) -> pymupdf.Rect:
    return pymupdf.Rect(image["bbox"])


def repeated_images(images: list[list[dict[str, Any]]]) -> set[bytes]:
    counts = Counter(digest for page in images for digest in {image["digest"] for image in page})
    return {digest for digest, count in counts.items() if count >= MIN_REPEATS}


def joined(boxes: list[Box]) -> list[Box]:
    """The boxes, those that touch or overlap made one, as sharp as the sharpest."""
    merged: list[Box] = []
    for box, sharpness in boxes:
        if box.is_empty:
            continue
        # A box may join several already merged, and bridge them.
        while touching := [other for other in merged if near(box, other[0])]:
            for other in touching:
                merged.remove(other)
                box = box | other[0]
                sharpness = max(sharpness, other[1])
        merged.append((box, sharpness))
    return merged


def near(box: pymupdf.Rect, other: pymupdf.Rect) -> bool:
    return bool((box + pymupdf.Rect(-TOUCHING, -TOUCHING, TOUCHING, TOUCHING)).intersects(other))


def is_on(line: Line, box: pymupdf.Rect) -> bool:
    """The line's middle is inside the box."""
    return bool(box.contains(pymupdf.Point((line.x0 + line.x1) / 2, (line.y0 + line.y1) / 2)))


def render(page: pymupdf.Page, box: pymupdf.Rect, sharpness: float) -> Picture:
    """The box as the page shows it, as sharp as its image but no bigger than MAX_SIDE."""
    zoom = min(sharpness, MAX_SIDE / max(box.width, box.height))
    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=box, alpha=False)
    image = to_cover(pixmap)
    return Picture(image.data, image.width, image.height, box.y0, box.y1)
