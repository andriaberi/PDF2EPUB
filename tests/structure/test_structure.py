import pytest

from bookflow.paragraphs import Paragraph
from bookflow.pdf import Line, Page
from bookflow.structure import Heading, build_sections
from bookflow.structure.headings import fix_label, label_level

LEFT, RIGHT = 45.0, 385.0


def body_page(number: int) -> Page:
    """A full page of ordinary text, so the text column can be measured."""
    lines = [Line("text", LEFT, 40 + 14 * row, RIGHT, 50 + 14 * row) for row in range(30)]
    return Page(number, 430, 590, lines)


def centred(text: str, page: int = 1, width: float = 90) -> Paragraph:
    middle = (LEFT + RIGHT) / 2
    line = Line(text, middle - width / 2, 100, middle + width / 2, 110)
    return Paragraph(text, page, [line])


def body(text: str, page: int = 1) -> Paragraph:
    return Paragraph(text, page, [Line(text, 62, 200, RIGHT, 210), Line("", LEFT, 214, 300, 224)])


PAGES = [body_page(1), body_page(2)]


def headings(paragraphs: list[Paragraph]) -> list[Heading | None]:
    return [section.heading for section in build_sections(paragraphs, PAGES)]


def test_label_and_title() -> None:
    sections = build_sections(
        [centred("თავი მეორე"), centred("კეთილგონიერება", width=150), body("ტექსტი.")], PAGES
    )
    assert [s.heading for s in sections] == [
        Heading(level=1, label="თავი მეორე", title="კეთილგონიერება")
    ]
    assert [p.text for p in sections[0].paragraphs] == ["ტექსტი."]


def test_label_without_title() -> None:
    assert headings([centred("Chapter 4"), body("Text.")]) == [Heading(1, "Chapter 4")]


def test_title_wrapped_over_two_lines() -> None:
    paragraphs = [
        centred("თავი მეხუთე"),
        centred("როგორ დიდხანს ხმარობდა მონსინიორ", width=230),
        centred("ბიენვენიუ ტანსაცმელს", width=130),
        body("ტექსტი."),
    ]
    [heading] = headings(paragraphs)
    assert heading is not None
    assert heading.title == "როგორ დიდხანს ხმარობდა მონსინიორ ბიენვენიუ ტანსაცმელს"


def test_levels_follow_the_division_words() -> None:
    paragraphs = [
        centred("წიგნი პირველი"),
        centred("კაცი მართალი"),
        centred("თავი პირველი"),
        centred("ბატონი მირიელი"),
        body("ტექსტი."),
    ]
    assert headings(paragraphs) == [
        Heading(1, "წიგნი პირველი", "კაცი მართალი"),
        Heading(2, "თავი პირველი", "ბატონი მირიელი"),
    ]


def test_text_before_the_first_heading_is_front_matter() -> None:
    sections = build_sections([body("Preface."), centred("Chapter 1"), body("Text.")], PAGES)
    assert sections[0].heading is None
    assert [p.text for p in sections[0].paragraphs] == ["Preface."]


def test_sentence_starting_with_a_label_word_is_text() -> None:
    assert headings([centred("Chapter 1"), body("თავი ჩაღუნა ბრევემ.")]) == [
        Heading(1, "Chapter 1")
    ]
    assert headings([centred("Chapter 1"), body("თავი დახარა")]) == [Heading(1, "Chapter 1")]


@pytest.mark.parametrize(
    ("text", "level"),
    [
        ("თავი მეორე", 4),
        ("თაჭი მეორე", 4),
        ("წიგნი მეხუთე", 3),
        ("CHAPTER XII.", 4),
        ("Part 2", 2),
        ("მესამე ნაწილი", 2),
        ("ტომი I", 1),
        ("Volume 2", 1),
    ],
)
def test_label_level(text: str, level: int) -> None:
    assert label_level(text) == level


@pytest.mark.parametrize(
    "text", ["თავი ჩაღუნა ბრევემ.", "ბატონი მირიელი", "Chapter", "მისი თავს", "მესამე ნაწილს"]
)
def test_not_labels(text: str) -> None:
    assert label_level(text) is None


@pytest.mark.parametrize(
    ("text", "fixed"),
    [
        ("თაჭი მეორე", "თავი მეორე"),
        ("Chaptcr 4", "Chapter 4"),
        ("CHAPTER 4", "CHAPTER 4"),
        ("მესამე ნაწილი", "მესამე ნაწილი"),
    ],
)
def test_fix_label(text: str, fixed: str) -> None:
    assert fix_label(text) == fixed


def flush(text: str, y: float, page: int = 1, x1: float = 160) -> Paragraph:
    """A short line set at the paragraph indent, as digital books often set headings."""
    return Paragraph(text, page, [Line(text, 50, y, x1, y + 11)])


def text(content: str, y: float, page: int = 1) -> Paragraph:
    lines = [Line(content, 50, y, RIGHT, y + 11), Line("", LEFT, y + 12, 300, y + 23)]
    return Paragraph(content, page, lines)


def test_flush_left_label_and_title() -> None:
    paragraphs = [
        flush("თავი მეთოთხმეტე", 158),
        flush("რას ფიქრობდა", 170),
        flush("ერთი უკანასკნელი სიტყვაც.", 195),
        text("შემდეგი აბზაცი.", 207),
    ]
    sections = build_sections(paragraphs, PAGES)
    assert [s.heading for s in sections] == [Heading(1, "თავი მეთოთხმეტე", "რას ფიქრობდა")]
    assert [p.text for p in sections[0].paragraphs] == [
        "ერთი უკანასკნელი სიტყვაც.",
        "შემდეგი აბზაცი.",
    ]


def test_flush_left_short_text_without_gap_is_not_a_title() -> None:
    paragraphs = [flush("Chapter 3", 100), flush("Yes.", 112), text("And then.", 124)]
    sections = build_sections(paragraphs, PAGES)
    assert [s.heading for s in sections] == [Heading(1, "Chapter 3")]


def test_title_run_into_the_text_is_split_off() -> None:
    title_and_text = Paragraph(
        "მხიარულების მხიარული დასასრული მარტო რომ დარჩნენ",
        2,
        [
            Line("მხიარულების მხიარული დასასრული", 50, 36, 200, 47),
            Line("მარტო რომ", LEFT, 48, RIGHT, 59),
            Line("დარჩნენ", LEFT, 60, 250, 71),
        ],
    )
    paragraphs = [flush("თავი მეცხრე", 560), title_and_text]
    [section] = build_sections(paragraphs, PAGES)
    assert section.heading == Heading(1, "თავი მეცხრე", "მხიარულების მხიარული დასასრული")
    assert [p.text for p in section.paragraphs] == ["მარტო რომ დარჩნენ"]


def test_part_book_and_chapter_levels() -> None:
    paragraphs = [
        flush("ნაწილი პირველი", 70),
        flush("ფანტინი", 82),
        flush("წიგნი პირველი", 110),
        flush("კაცი მართალი", 122),
        flush("თავი პირველი", 150),
        flush("ბატონი მირიელი", 162),
        text("1815 წელს.", 190),
    ]
    assert [h.level for h in headings(paragraphs) if h] == [1, 2, 3]


def big(text: str, y: float, size: float = 16) -> Paragraph:
    """A heading line in a bigger font than the text's 10 points."""
    return Paragraph(text, 1, [Line(text, LEFT, y, LEFT + 100, y + size)])


def test_label_in_a_bigger_font_without_title() -> None:
    paragraphs = [big("თავი მეორე", 100), flush("– რა ვქნა?", 130), text("ტექსტი.", 150)]
    [section] = build_sections(paragraphs, PAGES)
    assert section.heading == Heading(1, "თავი მეორე")
    assert [p.text for p in section.paragraphs] == ["– რა ვქნა?", "ტექსტი."]


def test_label_in_a_bigger_font_keeps_a_title_in_one() -> None:
    paragraphs = [big("თავი მეორე", 100), big("სტუმრები", 125), text("ტექსტი.", 160)]
    assert headings(paragraphs) == [Heading(1, "თავი მეორე", "სტუმრები")]


def test_volume_part_and_chapter_levels() -> None:
    paragraphs = [
        big("ტომი I", 60, size=28),
        big("მესამე ნაწილი", 100, size=18),
        big("თავი პირველი", 130),
        text("ტექსტი.", 160),
    ]
    assert headings(paragraphs) == [
        Heading(1, "ტომი I"),
        Heading(2, "ნაწილი მესამე"),
        Heading(3, "თავი პირველი"),
    ]


def test_label_order_follows_the_rest_of_the_book() -> None:
    paragraphs = [
        big("ნაწილი პირველი", 60, size=18),
        big("თავი პირველი", 100),
        text("ტექსტი.", 130),
        big("მესამე ნაწილი", 160, size=18),
        big("მეორე თავი", 200),
        text("ტექსტი.", 230),
    ]
    assert [h.label for h in headings(paragraphs) if h] == [
        "ნაწილი პირველი",
        "თავი პირველი",
        "ნაწილი მესამე",
        "თავი მეორე",
    ]


def test_label_order_can_follow_a_book_that_puts_the_number_first() -> None:
    paragraphs = [
        big("პირველი თავი", 60),
        text("ტექსტი.", 90),
        big("მეორე თავი", 120),
        text("ტექსტი.", 150),
        big("თავი მესამე", 180),
        text("ტექსტი.", 210),
    ]
    assert [h.label for h in headings(paragraphs) if h] == [
        "პირველი თავი",
        "მეორე თავი",
        "მესამე თავი",
    ]
