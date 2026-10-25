import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

from pdf2epub.cover import Cover
from pdf2epub.pipeline import (
    STEPS,
    ConvertError,
    Options,
    choose_cover,
    convert,
    read_book,
    write_book,
)
from pdf2epub.structure import Note


def test_writes_an_epub(make_pdf: Callable[..., str], tmp_path: Path) -> None:
    output = tmp_path / "out.epub"
    convert(Options(pdf=make_pdf([["Hello world."]])), output)
    assert zipfile.ZipFile(output).read("mimetype") == b"application/epub+zip"


def test_convert_reports_each_step(make_pdf: Callable[..., str], tmp_path: Path) -> None:
    steps: list[str] = []
    result = convert(Options(pdf=make_pdf([["Hello world."]])), tmp_path / "out.epub", steps.append)
    assert tuple(steps) == STEPS
    assert result.output == tmp_path / "out.epub"
    assert (result.headings, result.paragraphs, result.notes) == (0, 1, 0)


def test_convert_raises_instead_of_printing(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(ConvertError, match="no such file"):
        convert(Options(pdf="missing.pdf"), "out.epub")
    assert capsys.readouterr() == ("", "")


def test_reading_writes_nothing(make_pdf: Callable[..., str], tmp_path: Path) -> None:
    steps: list[str] = []
    book = read_book(Options(pdf=make_pdf([["Hello world."]])), steps.append)
    assert tuple(steps) == STEPS[:3]
    assert [p.text for s in book.sections for p in s.paragraphs] == ["Hello world."]
    assert sorted(path.name for path in tmp_path.iterdir()) == ["book.pdf"]


def test_writes_the_book_as_edited(make_pdf: Callable[..., str], tmp_path: Path) -> None:
    book = read_book(Options(pdf=make_pdf([["Hello world."]])))
    book.metadata.title = "Edited"
    book.sections[0].paragraphs[0].text = "Edited text."
    write_book(book, tmp_path / "out.epub")
    epub = zipfile.ZipFile(tmp_path / "out.epub")
    assert "<dc:title>Edited</dc:title>" in epub.read("EPUB/content.opf").decode()
    assert "Edited text." in epub.read("EPUB/text/section-0001.xhtml").decode()


def test_writing_leaves_the_book_as_it_was(make_pdf: Callable[..., str], tmp_path: Path) -> None:
    book = read_book(Options(pdf=make_pdf([["Hello world.[1]", "And more of the story."]])))
    note = Note("note-1", "1", "A note.")
    book.notes, book.sections[0].notes = [note], {"1": note}
    write_book(book, tmp_path / "first.epub")
    write_book(book, tmp_path / "second.epub")
    first = zipfile.ZipFile(tmp_path / "first.epub")
    second = zipfile.ZipFile(tmp_path / "second.epub")
    for name in first.namelist():
        if name != "EPUB/content.opf":  # it holds the time of writing
            assert first.read(name) == second.read(name), name
    assert 'href="../notes.xhtml#note-1"' in first.read("EPUB/text/section-0001.xhtml").decode()


def test_unwritable_output_is_reported(make_pdf: Callable[..., str], tmp_path: Path) -> None:
    book = read_book(Options(pdf=make_pdf([["Hello world."]])))
    with pytest.raises(ConvertError, match="can't write"):
        write_book(book, tmp_path / "missing" / "out.epub")


OWN = Cover(b"own", 1, 1)
GIVEN = Cover(b"given", 1, 1)


@pytest.mark.parametrize(
    ("own", "given", "chosen"),
    [(OWN, GIVEN, OWN), (OWN, None, OWN), (None, GIVEN, GIVEN), (None, None, None)],
)
def test_the_books_own_cover_comes_first(
    own: Cover | None, given: Cover | None, chosen: Cover | None
) -> None:
    assert choose_cover(own, given)[0] is chosen


def test_given_cover_is_used_without_a_cover_in_the_pdf(
    make_pdf: Callable[..., str], tmp_path: Path
) -> None:
    import pymupdf

    image = tmp_path / "cover.png"
    pymupdf.open().new_page().get_pixmap().save(image)
    output = tmp_path / "out.epub"
    result = convert(Options(pdf=make_pdf([["Hello."]]), cover=str(image)), output)
    assert result.cover == "cover from the given image"
    assert "EPUB/images/cover.jpg" in zipfile.ZipFile(output).namelist()


def test_bad_cover_file_is_reported(make_pdf: Callable[..., str], tmp_path: Path) -> None:
    with pytest.raises(ConvertError, match="no such cover image"):
        convert(Options(pdf=make_pdf([["Hello."]]), cover="missing.png"), tmp_path / "out.epub")
