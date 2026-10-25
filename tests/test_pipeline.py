import io
import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

from pdf2epub.book import TextBlock
from pdf2epub.cover import Cover
from pdf2epub.errors import BookError, ConvertError
from pdf2epub.paragraphs import Paragraph
from pdf2epub.pipeline import (
    STEPS,
    Options,
    choose_cover,
    convert,
    place_by_page,
    read_book,
    with_left_out,
    write_book,
)
from pdf2epub.structure import Heading, Note, Section


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
    assert [block.text for block in book.blocks if isinstance(block, TextBlock)] == ["Hello world."]
    assert sorted(path.name for path in tmp_path.iterdir()) == ["book.pdf"]


def test_writes_the_book_as_edited(make_pdf: Callable[..., str], tmp_path: Path) -> None:
    book = read_book(Options(pdf=make_pdf([["Hello world."]])))
    book.metadata.title = "Edited"
    assert isinstance(book.blocks[0], TextBlock)
    book.blocks[0].text = "Edited text."
    write_book(book, tmp_path / "out.epub")
    epub = zipfile.ZipFile(tmp_path / "out.epub")
    assert "<dc:title>Edited</dc:title>" in epub.read("EPUB/content.opf").decode()
    assert "Edited text." in epub.read("EPUB/text/section-0001.xhtml").decode()


def test_writing_leaves_the_book_as_it_was(make_pdf: Callable[..., str], tmp_path: Path) -> None:
    book = read_book(Options(pdf=make_pdf([["Hello world.[1]", "And more of the story."]])))
    assert isinstance(book.blocks[0], TextBlock)
    book.notes = [Note("note-1", "1", "A note.")]
    book.blocks[0].notes = {"1": "note-1"}
    write_book(book, tmp_path / "first.epub")
    write_book(book, tmp_path / "second.epub")
    first = zipfile.ZipFile(tmp_path / "first.epub")
    second = zipfile.ZipFile(tmp_path / "second.epub")
    for name in first.namelist():
        if name != "EPUB/content.opf":  # it holds the time of writing
            assert first.read(name) == second.read(name), name
    assert 'href="../notes.xhtml#note-1"' in first.read("EPUB/text/section-0001.xhtml").decode()


def test_book_without_its_notes(make_pdf: Callable[..., str], tmp_path: Path) -> None:
    book = read_book(Options(pdf=make_pdf([["Hello world.[1]", "And more of the story."]])))
    assert isinstance(book.blocks[0], TextBlock)
    book.notes = [Note("note-1", "1", "A note.")]
    book.blocks[0].notes = {"1": "note-1"}
    book.include_notes = False
    result = write_book(book, tmp_path / "out.epub")
    epub = zipfile.ZipFile(tmp_path / "out.epub")
    assert "EPUB/notes.xhtml" not in epub.namelist()
    assert "Hello world. And more" in epub.read("EPUB/text/section-0001.xhtml").decode()
    assert result.notes == 0


def test_left_out_text_comes_back_but_not_text_made_into_notes() -> None:
    title_page = Paragraph("The Title", 1, role="title-page")
    text, notes = Paragraph("Text.[1]", 2), Paragraph("[1] A note.", 9)
    front, chapter = Section(None, [title_page]), Section(Heading(1, "Chapter 1"), [text, notes])
    everything = [(section, list(section.paragraphs)) for section in [front, chapter]]
    chapter.paragraphs.remove(notes)  # as extract_notes() does
    chapter.notes = {"1": Note("note-1", "1", "A note.")}
    sections = with_left_out(everything, [chapter])
    assert [(s.heading, s.paragraphs) for s in sections] == [
        (None, [title_page]),
        (Heading(1, "Chapter 1"), [text]),
    ]
    assert sections[1].notes == chapter.notes


def placed(page: int) -> list[list[str]]:
    sections = [
        Section(None, [Paragraph("Front", 2)]),
        Section(Heading(1, "Chapter 1", page=3), [Paragraph("A", 3), Paragraph("B", 5)]),
        Section(Heading(1, "Chapter 2", page=7), [Paragraph("C", 7)]),
    ]
    place_by_page(sections, Paragraph("Contents", page, role="contents"))
    return [[p.text for p in section.paragraphs] for section in sections]


@pytest.mark.parametrize(
    ("page", "where"),
    [
        (1, [["Contents", "Front"], ["A", "B"], ["C"]]),
        (2, [["Front", "Contents"], ["A", "B"], ["C"]]),
        (4, [["Front"], ["A", "Contents", "B"], ["C"]]),
        (6, [["Front"], ["A", "B", "Contents"], ["C"]]),
        (8, [["Front"], ["A", "B"], ["C", "Contents"]]),
    ],
)
def test_contents_placed_by_their_page(page: int, where: list[list[str]]) -> None:
    assert placed(page) == where


def test_contents_before_the_first_heading_start_the_book() -> None:
    sections = [Section(Heading(1, "Chapter 1", page=3), [Paragraph("A", 3)])]
    place_by_page(sections, Paragraph("Contents", 2, role="contents"))
    assert [(s.heading, [p.text for p in s.paragraphs]) for s in sections] == [
        (None, ["Contents"]),
        (Heading(1, "Chapter 1"), ["A"]),
    ]


def test_printed_contents_are_left_out_until_asked_for(
    make_pdf: Callable[..., str], tmp_path: Path
) -> None:
    entries = [f"Chapter {n} ........ {n * 10}" for n in range(1, 7)]
    pdf = make_pdf([["Hello world."] * 3, ["Contents", *entries]])
    book = read_book(Options(pdf=pdf))
    [contents] = [block for block in book.blocks if block.role == "contents"]
    assert (contents.page, contents.include) == (2, False)
    write_book(book, tmp_path / "out.epub")
    text = zipfile.ZipFile(tmp_path / "out.epub").read("EPUB/text/section-0001.xhtml").decode()
    assert "Chapter 1" not in text
    contents.include = True
    write_book(book, tmp_path / "out.epub")
    text = zipfile.ZipFile(tmp_path / "out.epub").read("EPUB/text/section-0001.xhtml").decode()
    assert '<div class="verse"><p>Contents</p><p>Chapter 1 ........ 10</p>' in text


def test_book_with_problems_is_not_written(make_pdf: Callable[..., str], tmp_path: Path) -> None:
    book = read_book(Options(pdf=make_pdf([["Hello world."]])))
    book.metadata.title = ""
    for block in book.blocks:
        block.role = "unknown"
    with pytest.raises(BookError, match=r"^the book needs a title; block 'b1': unknown role"):
        write_book(book, tmp_path / "out.epub")
    assert not (tmp_path / "out.epub").exists()


def test_error_names_the_first_problems_only(make_pdf: Callable[..., str], tmp_path: Path) -> None:
    book = read_book(Options(pdf=make_pdf([["Hello world."]])))
    book.blocks *= 8
    with pytest.raises(BookError, match=r"; and 2 more$"):
        write_book(book, tmp_path / "out.epub")


def test_writes_to_a_file_object(make_pdf: Callable[..., str], tmp_path: Path) -> None:
    book = read_book(Options(pdf=make_pdf([["Hello world."]])))
    buffer = io.BytesIO()
    result = write_book(book, buffer)
    assert result.output is None
    epub = zipfile.ZipFile(buffer)
    assert "Hello world." in epub.read("EPUB/text/section-0001.xhtml").decode()


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


def test_given_cover_may_be_image_bytes(make_pdf: Callable[..., str], tmp_path: Path) -> None:
    import pymupdf

    image = pymupdf.open().new_page().get_pixmap().tobytes("png")
    result = convert(Options(pdf=make_pdf([["Hello."]]), cover=image), tmp_path / "out.epub")
    assert result.cover == "cover from the given image"


def test_bad_cover_file_is_reported(make_pdf: Callable[..., str], tmp_path: Path) -> None:
    with pytest.raises(ConvertError, match="no such cover image"):
        convert(Options(pdf=make_pdf([["Hello."]]), cover="missing.png"), tmp_path / "out.epub")
