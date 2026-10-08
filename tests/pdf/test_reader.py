from collections.abc import Callable
from pathlib import Path

import pytest

from pdf2epub.pdf import Line, ReadError, read_pdf
from pdf2epub.pdf.reader import merge_rows, metadata_text

MakePdf = Callable[..., str]


def test_reads_lines_without_page_numbers_or_headers(make_pdf: MakePdf) -> None:
    pages = [[f"Line one of page {n}.", "Line two."] for n in range(1, 5)]
    book = read_pdf(make_pdf(pages, header="A Running Header"))
    assert [page.number for page in book.pages] == [1, 2, 3, 4]
    assert [line.text for line in book.pages[2].lines] == ["Line one of page 3.", "Line two."]


def test_reads_selected_pages(make_pdf: MakePdf) -> None:
    book = read_pdf(make_pdf([["one"], ["two"], ["three"]]), "2-3")
    assert [page.number for page in book.pages] == [2, 3]


def test_detects_language(make_pdf: MakePdf) -> None:
    book = read_pdf(make_pdf([["It was the best of times, it was the worst of times."]]))
    assert book.language == "en"


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ReadError, match="no such file"):
        read_pdf(str(tmp_path / "missing.pdf"))


def test_not_a_pdf(tmp_path: Path) -> None:
    path = tmp_path / "book.pdf"
    path.write_text("hello")
    with pytest.raises(ReadError, match="not a readable PDF"):
        read_pdf(str(path))


def test_no_text_layer(make_pdf: MakePdf, tmp_path: Path) -> None:
    import pymupdf

    path = tmp_path / "blank.pdf"
    doc = pymupdf.open()
    doc.new_page()
    doc.save(path)
    with pytest.raises(ReadError, match="no text found"):
        read_pdf(str(path))


@pytest.mark.parametrize(
    ("value", "kept"),
    [
        ("ჰეროდოტე", "ჰეროდოტე"),
        ("Admin", None),
        ("USER", None),
        ("Microsoft Word - draft.doc", None),
        ("000427", None),
        (None, None),
    ],
)
def test_metadata_text(value: str | None, kept: str | None) -> None:
    assert metadata_text(value) == kept


def test_pieces_of_one_printed_line_are_joined() -> None:
    pieces = [Line("ორი", 120, 100, 150, 112), Line("ერთი", 50, 100, 110, 112)]
    assert [line.text for line in merge_rows(pieces)] == ["ერთი ორი"]


def test_a_heading_level_with_an_epigraph_is_a_line_of_its_own() -> None:
    pieces = [Line("ნაწილი პირველი", 55, 415, 167, 437), Line("ჰობსი", 484, 411, 517, 424)]
    assert [line.text for line in merge_rows(pieces)] == ["ჰობსი", "ნაწილი პირველი"]
