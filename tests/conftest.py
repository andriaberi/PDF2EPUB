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
