from pathlib import Path

import pymupdf
import pytest


@pytest.fixture
def make_pdf(tmp_path: Path):  # type: ignore[no-untyped-def]
    """Write a PDF whose pages hold the given lines, top to bottom, plus a page number."""

    def make(pages: list[list[str]], header: str | None = None) -> str:
        doc = pymupdf.open()
        for number, lines in enumerate(pages, start=1):
            page = doc.new_page(width=400, height=600)
            if header:
                page.insert_text((60, 30), header, fontsize=9)
            for row, text in enumerate(lines):
                page.insert_text((60, 90 + row * 16), text, fontsize=11)
            page.insert_text((195, 580), str(number), fontsize=9)
        path = tmp_path / "book.pdf"
        doc.save(path)
        return str(path)

    return make


# Lines of text as in a book, top to bottom of the page.
TEXT = [f"Line {row} of the story goes on and on here." for row in range(30)]


@pytest.fixture
def make_picture_pdf(tmp_path: Path):  # type: ignore[no-untyped-def]
    """Write a PDF of text pages with pictures printed on them."""

    def make(
        pictures: dict[int, list[tuple[float, float, float, float]]],
        pages: int = 4,
        labels: int = 0,
    ) -> str:
        """Pages of text with gaps where pictures go: {page index: [(x0, y0, x1, y1)]}, each
        with `labels` lines of text printed on it."""
        image = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 200, 100), False)
        image.set_rect(image.irect, (200, 60, 40))
        doc = pymupdf.open()
        for number in range(pages):
            page = doc.new_page(width=400, height=600)
            boxes = pictures.get(number, [])
            y = 60.0
            for text in TEXT:
                while any(y0 - 4 <= y <= y1 + 14 for _, y0, _, y1 in boxes):
                    y += 14
                if y > 560:
                    break
                page.insert_text((50, y), text, fontsize=10)
                y += 14
            for box in boxes:
                page.insert_image(pymupdf.Rect(box), pixmap=image, keep_proportion=False)
                for row in range(labels):
                    page.insert_text((box[0] + 10, box[1] + 15 + 12 * row), "Label", fontsize=8)
            page.insert_text((195, 585), str(number + 1), fontsize=9)
        path = tmp_path / "pictures.pdf"
        doc.save(path)
        return str(path)

    return make
