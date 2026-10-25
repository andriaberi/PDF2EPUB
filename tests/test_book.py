import json
from collections.abc import Callable
from typing import Any

import pytest

from pdf2epub.book import Book, BookError, HeadingBlock, TextBlock
from pdf2epub.cover import Cover
from pdf2epub.epub import Metadata
from pdf2epub.paragraphs import Paragraph
from pdf2epub.pdf import Line
from pdf2epub.structure import Heading, Note, Section

ONE = Note("note-1", "1", "The first volume's note.")
OTHER_ONE = Note("note-2", "1", "The second volume's note.")


def line(text: str) -> Line:
    return Line(text, 10, 20, 30, 40)


def sample_sections() -> list[Section]:
    lines = [line("A sung line[1]"), line("and another")]
    verse = Paragraph("A sung line[1] and another", 3, lines, verse=True)
    return [
        Section(None, [Paragraph("Before the first heading.", 1, [line("x")])]),
        Section(Heading(1, "Volume I", page=2)),
        Section(
            Heading(2, "Chapter 1", "The start", page=3),
            [
                Paragraph("A quotation.", 3, [line("x")], epigraph=True),
                Paragraph("Its author", 3, [line("x")], epigraph=True, attribution=True),
                Paragraph("Text with a note.[1]", 3, [line("x")]),
                verse,
            ],
            {"1": ONE},
        ),
        Section(Heading(1, "Volume II", page=9)),
        Section(Heading(2, "Chapter 1", page=9), [Paragraph("Again.[1]", 9)], {"1": OTHER_ONE}),
    ]


def sample_book() -> Book:
    metadata = Metadata("Title", "Author", "en", "urn:uuid:1")
    cover = Cover(b"\xff\xd8 image", 600, 800)
    return Book.from_sections(
        metadata, sample_sections(), [ONE, OTHER_ONE], cover, "cover from the PDF"
    )


def shape(sections: list[Section]) -> list[tuple[object, ...]]:
    """What the EPUB is written from: the lines only matter for verse."""
    return [
        (
            section.heading,
            section.heading.page if section.heading else None,
            [
                (p.text, p.page, p.verse, p.epigraph, p.attribution, [x.text for x in p.lines])
                if p.verse
                else (p.text, p.page, p.verse, p.epigraph, p.attribution)
                for p in section.paragraphs
            ],
            section.notes,
        )
        for section in sections
    ]


def test_blocks_give_back_the_sections() -> None:
    assert shape(sample_book().sections()) == shape(sample_sections())


def test_blocks_in_reading_order() -> None:
    blocks = sample_book().blocks
    assert [type(b).__name__ for b in blocks] == [
        "TextBlock",
        *["HeadingBlock", "HeadingBlock", "TextBlock", "TextBlock", "TextBlock", "TextBlock"],
        *["HeadingBlock", "HeadingBlock", "TextBlock"],
    ]
    assert len({b.id for b in blocks}) == len(blocks)
    verse = blocks[6]
    assert isinstance(verse, TextBlock)
    assert (verse.verse, verse.lines, verse.notes) == (
        True,
        ["A sung line[1]", "and another"],
        {"1": "note-1"},
    )


def test_marks_link_by_note_id_not_number() -> None:
    sections = sample_book().sections()
    assert sections[2].notes == {"1": ONE}
    assert sections[4].notes == {"1": OTHER_ONE}


def test_left_out_heading_joins_its_text_to_the_section_before() -> None:
    book = sample_book()
    book.blocks[2].include = False  # "Chapter 1" of volume I
    sections = book.sections()
    assert [s.heading.label if s.heading else None for s in sections] == [
        None,
        "Volume I",
        "Volume II",
        "Chapter 1",
    ]
    assert len(sections[1].paragraphs) == 4


def test_left_out_text_is_not_written() -> None:
    book = sample_book()
    book.blocks[0].include = False
    assert book.sections()[0].heading == Heading(1, "Volume I")


def test_data_is_json_and_reads_back_the_same() -> None:
    book = sample_book()
    data = json.loads(json.dumps(book.to_dict()))
    assert data["version"] == 1
    assert data["blocks"][1] == {
        "type": "heading",
        "id": "b2",
        "page": 2,
        "role": "body",
        "include": True,
        "level": 1,
        "label": "Volume I",
        "title": None,
    }
    assert Book.from_dict(data) == book


def test_book_without_a_cover_reads_back() -> None:
    book = sample_book()
    book.cover, book.cover_source = None, "no cover"
    assert Book.from_dict(book.to_dict()) == book


def test_other_version_is_refused() -> None:
    data = sample_book().to_dict()
    data["version"] = 2
    with pytest.raises(BookError, match="version 2"):
        Book.from_dict(data)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda d: d["blocks"][0].update(type="image"), "unknown block type"),
        (lambda d: d["blocks"][0].pop("text"), "bad book data"),
        (lambda d: d["blocks"][0].update(colour="red"), "bad book data"),
        (lambda d: d.pop("metadata"), "bad book data"),
        (lambda d: d["cover"].update(data="not base64!"), "bad book data"),
    ],
)
def test_broken_data_is_refused(change: Callable[[dict[str, Any]], object], message: str) -> None:
    data = sample_book().to_dict()
    change(data)
    with pytest.raises(BookError, match=message):
        Book.from_dict(data)


def test_block_kinds_are_exported() -> None:
    import pdf2epub

    assert (pdf2epub.HeadingBlock, pdf2epub.TextBlock) == (HeadingBlock, TextBlock)
