import json
from collections.abc import Callable
from typing import Any

import pytest

from pdf2epub.book import Book, HeadingBlock, PictureBlock, TextBlock, without_marks
from pdf2epub.cover import Cover
from pdf2epub.epub import Metadata
from pdf2epub.errors import BookError, ConvertError
from pdf2epub.paragraphs import Paragraph
from pdf2epub.pdf import Line, Picture
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


METADATA = Metadata("Title", "Author", "en", "urn:uuid:1")


def sample_book() -> Book:
    cover = Cover(b"\xff\xd8 image", 600, 800)
    return Book.from_sections(
        METADATA, sample_sections(), [ONE, OTHER_ONE], cover, "cover from the PDF"
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


def test_only_the_body_is_shown_at_first() -> None:
    sections = sample_sections()
    preface = Section(Heading(1, "Preface", page=1, role="preface"))
    preface.paragraphs.append(Paragraph("Why I wrote it.", 1, role="preface"))
    book = Book.from_sections(METADATA, [preface, *sections], [ONE, OTHER_ONE], None, "")
    assert [(b.role, b.include) for b in book.blocks[:3]] == [
        ("preface", False),
        ("preface", False),
        ("body", True),
    ]
    assert shape(book.sections()) == shape(sections)
    book.blocks[0].include = book.blocks[1].include = True
    first = book.sections()[0]
    assert first.heading == preface.heading
    assert first.paragraphs[0] == preface.paragraphs[0]


def texts(sections: list[Section]) -> list[str]:
    return [p.text for section in sections for p in section.paragraphs]


def test_notes_left_out_take_their_marks_with_them() -> None:
    book = sample_book()
    book.include_notes = False
    sections = book.sections()
    assert texts(sections) == [
        "Before the first heading.",
        "A quotation.",
        "Its author",
        "Text with a note.",
        "A sung line and another",
        "Again.",
    ]
    assert [line.text for line in sections[2].paragraphs[3].lines] == ["A sung line", "and another"]
    assert all(not section.notes for section in sections)
    assert book.written_notes() == []


def test_removed_note_takes_only_its_own_marks() -> None:
    book = sample_book()
    book.notes.remove(OTHER_ONE)
    sections = book.sections()
    assert texts(sections)[-1] == "Again."
    assert texts(sections)[3] == "Text with a note.[1]"
    assert sections[2].notes == {"1": ONE}


def test_marks_never_linked_stay_as_printed() -> None:
    book = sample_book()
    book.include_notes = False
    book.blocks.append(TextBlock(id="new", page=10, text="Printed as [7] in the book."))
    assert texts(book.sections())[-1] == "Printed as [7] in the book."


@pytest.mark.parametrize(
    ("text", "left"),
    [
        ("word.[1] Next", "word. Next"),
        ("word [1] next", "word next"),
        ("end[1]", "end"),
        ("one[1] two[2]", "one two[2]"),
        ("[12] stays, [1] goes", "[12] stays, goes"),
    ],
)
def test_without_marks(text: str, left: str) -> None:
    assert without_marks(text, {"1"}) == left


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


def test_book_without_a_cover_or_notes_reads_back() -> None:
    book = sample_book()
    book.cover, book.cover_source = None, "no cover"
    book.include_notes = False
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


def test_bad_book_data_is_a_conversion_error_too() -> None:
    assert issubclass(BookError, ConvertError)


def test_book_as_read_has_no_problems() -> None:
    assert sample_book().problems() == []


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        (lambda d: d["metadata"].update(title=" "), "the book needs a title"),
        (lambda d: d["metadata"].update(language=""), "the book needs a language"),
        (lambda d: d["metadata"].update(author=3), "the author must be text"),
        (lambda d: d["blocks"][1].update(id="b1"), "block 'b1': each block needs an id"),
        (lambda d: d["blocks"][1].update(page=-1), "block 'b2': its page must be a whole"),
        (lambda d: d["blocks"][1].update(page="2"), "block 'b2': its page must be a whole"),
        (lambda d: d["blocks"][1].update(role="appendix"), "block 'b2': unknown role 'appendix'"),
        (lambda d: d["blocks"][1].update(include="yes"), "block 'b2': include must be"),
        (lambda d: d["blocks"][1].update(level=7), "block 'b2': a heading's level must be 1 to 6"),
        (lambda d: d["blocks"][1].update(level=0), "block 'b2': a heading's level must be 1 to 6"),
        (lambda d: d["blocks"][1].update(label=""), "block 'b2': a heading needs a label"),
        (lambda d: d["blocks"][1].update(title=["x"]), "block 'b2': a heading's title must be"),
        (lambda d: d["blocks"][0].update(text=" "), "block 'b1' has no text"),
        (
            lambda d: d["blocks"][0].update(epigraph=1),
            "block 'b1': verse, epigraph and attribution",
        ),
        (lambda d: d["blocks"][6].update(lines=[]), "block 'b7': verse needs its lines"),
        (lambda d: d["blocks"][6].update(lines="a line"), "block 'b7': lines must be a list"),
        (lambda d: d["blocks"][6].update(notes={"1": 1}), "block 'b7': notes must map each mark"),
        (lambda d: [b.update(include=False) for b in d["blocks"]], "no block is included"),
        (lambda d: d["notes"][1].update(id="note-1"), "note 'note-1': each note needs an id"),
        (lambda d: d["notes"][0].update(mark="*"), "note 'note-1': its mark must be a number"),
        (lambda d: d["notes"][0].update(text=""), "note 'note-1' has no text"),
        (lambda d: d.update(include_notes="no"), "include_notes must be true or false"),
        (lambda d: d["cover"].update(data="UE5H"), "the cover must be a JPEG image"),
        (lambda d: d["cover"].update(width=0), "the cover must be a JPEG image"),
    ],
)
def test_problems_in_edited_data(change: Callable[[dict[str, Any]], object], problem: str) -> None:
    data = sample_book().to_dict()
    change(data)
    problems = Book.from_dict(data).problems()
    assert len(problems) == 1
    assert problems[0].startswith(problem)


def test_cover_replaced_by_an_uploaded_image() -> None:
    import pymupdf

    book = sample_book()
    book.set_cover(pymupdf.open().new_page(width=60, height=90).get_pixmap().tobytes("png"))
    assert book.cover is not None
    assert (book.cover.width, book.cover.height, book.cover_source) == (
        60,
        90,
        "cover from the given image",
    )
    assert book.problems() == []


def test_upload_that_is_not_an_image_is_a_conversion_error() -> None:
    book = sample_book()
    with pytest.raises(ConvertError, match="not an image"):
        book.set_cover(b"hello")
    assert book.cover_source == "cover from the PDF"


def test_text_keeps_its_italics_in_tags() -> None:
    styled = Line(
        "a very good day", 0, 0, 0, 0, runs=[("a ", ""), ("very", "i"), (" good day", "")]
    )
    sections = [
        Section(None, [Paragraph("a very good day", 1, [styled])]),
        Section(None, [Paragraph("a very good day", 1, [styled], verse=True)]),
    ]
    prose, verse = Book.from_sections(METADATA, sections, [], None, "no cover").blocks
    assert isinstance(prose, TextBlock) and isinstance(verse, TextBlock)
    assert prose.text == "a <i>very</i> good day"
    assert verse.lines == ["a <i>very</i> good day"]


def test_a_styled_scene_break_stays_as_printed() -> None:
    stars = Line("* * *", 0, 0, 0, 0, runs=[("* * *", "b")])
    book = Book.from_sections(
        METADATA, [Section(None, [Paragraph("* * *", 1, [stars])])], [], None, "no cover"
    )
    assert isinstance(block := book.blocks[0], TextBlock) and block.text == "* * *"


def pictured_book() -> Book:
    picture = Paragraph("", 2, picture=Picture(b"\xff\xd8 picture", 300, 200, 10, 20))
    sections = [Section(None, [Paragraph("Text.", 1, [line("x")]), picture])]
    return Book.from_sections(METADATA, sections, [], None, "no cover")


def test_a_picture_is_a_block_of_its_own() -> None:
    _, picture = pictured_book().blocks
    assert isinstance(picture, PictureBlock)
    assert (picture.page, picture.data, picture.width, picture.height) == (
        2,
        b"\xff\xd8 picture",
        300,
        200,
    )
    (section,) = pictured_book().sections()
    assert section.paragraphs[1].picture is not None
    assert section.paragraphs[1].picture.data == b"\xff\xd8 picture"


def test_a_picture_reads_back_from_data() -> None:
    book = pictured_book()
    data = json.loads(json.dumps(book.to_dict()))
    assert data["blocks"][1]["type"] == "picture"
    assert Book.from_dict(data) == book


def test_a_picture_must_be_a_jpeg() -> None:
    book = pictured_book()
    picture = book.blocks[1]
    assert isinstance(picture, PictureBlock)
    picture.data = b"GIF89a"
    assert book.problems() == [
        "block 'b2': a picture must be a JPEG image with its width and height"
    ]
