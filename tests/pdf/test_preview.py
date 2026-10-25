from collections.abc import Callable

import pymupdf
import pytest

from pdf2epub.errors import ConvertError
from pdf2epub.pdf import render_page


def test_page_as_png_of_the_width_asked(make_pdf: Callable[..., str]) -> None:
    pdf = make_pdf([["First page."], ["Second page."]])
    image = render_page(pdf, 2, width=200)
    assert image.startswith(b"\x89PNG")
    pixmap = pymupdf.Pixmap(image)
    assert (pixmap.width, pixmap.height) == (200, 300)


@pytest.mark.parametrize(
    ("number", "width", "message"),
    [
        (0, 800, "no page 0: the PDF has 2"),
        (3, 800, "no page 3: the PDF has 2"),
        (1, 0, "1 to 3000 pixels wide, not 0"),
        (1, 5000, "1 to 3000 pixels wide, not 5000"),
    ],
)
def test_pages_and_widths_out_of_range(
    make_pdf: Callable[..., str], number: int, width: int, message: str
) -> None:
    pdf = make_pdf([["First page."], ["Second page."]])
    with pytest.raises(ConvertError, match=message):
        render_page(pdf, number, width)


def test_missing_pdf() -> None:
    with pytest.raises(ConvertError, match="no such file"):
        render_page("missing.pdf", 1)
