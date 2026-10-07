import pytest

from bookflow.labels import fix_label, is_section_name, label_level, numeral_value, split_label
from bookflow.paragraphs import Paragraph
from bookflow.pdf import Line, Page
from bookflow.structure import Heading, build_sections

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


@pytest.mark.parametrize(
    ("text", "value"),
    [("I", 1), ("IV", 4), ("XII.", 12), ("XXXIV", 34), ("7", 7), ("12.", 12)],
)
def test_numeral_value(text: str, value: int) -> None:
    assert numeral_value(text) == value


@pytest.mark.parametrize("text", ["IIII", "IC", "i", "v", "0", "1832", "I a", "Il"])
def test_not_numerals(text: str) -> None:
    assert numeral_value(text) is None


def numbered(*items: str) -> list[Paragraph]:
    """Chapter numbers flush left, each followed by a paragraph of text."""
    paragraphs = []
    for number, item in enumerate(items):
        y = 100 + 60 * number
        paragraphs += [flush(item, y, x1=80), text(f"ტექსტი {item}.", y + 20)]
    return paragraphs


def test_chapters_numbered_in_roman() -> None:
    sections = build_sections(numbered("I", "II", "III", "IV"), PAGES)
    assert [s.heading for s in sections] == [Heading(1, n) for n in ("I", "II", "III", "IV")]
    assert [p.text for p in sections[1].paragraphs] == ["ტექსტი II."]


def test_numbering_starts_again_in_each_part() -> None:
    paragraphs = [flush("ნაწილი პირველი", 50), *numbered("I", "II"), flush("ნაწილი მეორე", 400)]
    paragraphs += numbered("I", "II")
    labels = [
        (s.heading.level, s.heading.label) for s in build_sections(paragraphs, PAGES) if s.heading
    ]
    assert labels == [
        (1, "ნაწილი პირველი"),
        (2, "I"),
        (2, "II"),
        (1, "ნაწილი მეორე"),
        (2, "I"),
        (2, "II"),
    ]


def test_a_part_label_doesnt_take_the_chapter_number_as_its_title() -> None:
    paragraphs = [flush("ნაწილი პირველი", 50), *numbered("I", "II", "III")]
    assert build_sections(paragraphs, PAGES)[0].heading == Heading(1, "ნაწილი პირველი")


def test_numbers_out_of_step_are_text() -> None:
    # Too few to be chapter numbers, or not counting up: a number in the text.
    assert [s.heading for s in build_sections(numbered("7", "II"), PAGES)] == [None]
    sections = build_sections(numbered("I", "II", "III", "XX"), PAGES)
    assert [s.heading.label for s in sections if s.heading] == ["I", "II", "III"]


def test_sentence_after_a_chapter_number_is_not_its_title() -> None:
    paragraphs = numbered("I", "II", "III")
    paragraphs.insert(1, flush("ლევინმა სასმისი გამოცალა.", 120, x1=250))
    sections = build_sections(paragraphs, PAGES)
    assert sections[0].heading == Heading(1, "I")
    assert sections[0].paragraphs[0].text == "ლევინმა სასმისი გამოცალა."


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


def test_line_leading_into_speech_is_not_a_title() -> None:
    # The page ends after it, so only its colon tells it from a title.
    paragraphs = [
        flush("თავი მერვე", 512),
        flush("მზის სხივი ღრმა ორმოში", 524),
        flush("მამასთან მივიდა და უთხრა:", 548, x1=250),
    ]
    [section] = build_sections(paragraphs, PAGES)
    assert section.heading == Heading(1, "თავი მერვე", "მზის სხივი ღრმა ორმოში")
    assert [p.text for p in section.paragraphs] == ["მამასთან მივიდა და უთხრა:"]


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


@pytest.mark.parametrize(
    ("text", "split"),
    [
        ("თავი მეშვიდე გასეირნება სანაპიროზე", ("თავი მეშვიდე", "გასეირნება სანაპიროზე")),
        ("თავი მეექვსე - FONTIS", ("თავი მეექვსე", "FONTIS")),
        ("თავი მეექვსე -", ("თავი მეექვსე", "")),
        ("Chapter 3 The Storm", ("Chapter 3", "The Storm")),
    ],
)
def test_split_label(text: str, split: tuple[str, str]) -> None:
    assert split_label(text) == split


@pytest.mark.parametrize(
    "text", ["თავი მეორედ დახარა.", "თავი დახარა და წავიდა", "თავი მეშვიდე", "მისი თავი მეორე იყო"]
)
def test_not_split_labels(text: str) -> None:
    assert split_label(text) is None


@pytest.mark.parametrize("text", ["წინათქმა", "EPILOGUE", "Prologue", "ეპილოგი"])
def test_section_names(text: str) -> None:
    assert is_section_name(text)


def test_label_and_title_on_one_line() -> None:
    paragraphs = [flush("თავი მეშვიდე გასეირნება სანაპიროზე", 100, x1=300), text("ტექსტი.", 112)]
    sections = build_sections(paragraphs, PAGES)
    assert [s.heading for s in sections] == [Heading(1, "თავი მეშვიდე", "გასეირნება სანაპიროზე")]
    assert [p.text for p in sections[0].paragraphs] == ["ტექსტი."]


def test_label_and_dash_take_the_title_below() -> None:
    paragraphs = [flush("თავი მეექვსე -", 100), flush("მცირე რამ ისტორიიდან", 112)]
    paragraphs.append(text("ტექსტი.", 140))
    assert headings(paragraphs) == [Heading(1, "თავი მეექვსე", "მცირე რამ ისტორიიდან")]


def test_named_section_is_a_heading_at_the_outermost_level() -> None:
    paragraphs = [flush("წინათქმა", 50), text("წინასიტყვა.", 62)]
    paragraphs += [flush("ნაწილი პირველი", 50, page=2), flush("თავი პირველი", 100, page=2)]
    paragraphs.append(text("ტექსტი.", 200, page=2))
    assert headings(paragraphs) == [
        Heading(1, "წინათქმა"),
        Heading(1, "ნაწილი პირველი"),
        Heading(2, "თავი პირველი"),
    ]


def test_title_in_capitals_may_fill_the_line() -> None:
    title = "SOLUS CUM SOLO, IN LOCO REMOTO, NON COGITABUNTUR ORARE PATER NOSTER"
    paragraphs = [flush("თავი მეცამეტე", 100), text(title, 112), text("ფიქრს გაეტაცა.", 150)]
    assert headings(paragraphs) == [Heading(1, "თავი მეცამეტე", title)]


def test_title_as_long_as_a_line() -> None:
    title = Paragraph(
        "წინასწარ უნდა ყოფილიყო ჯაჭვი განზრახ დაზიანებული, რომ ასე ადვილად გამწყდარიყო",
        1,
        [
            Line("წინასწარ უნდა ყოფილიყო ჯაჭვი", 50, 112, RIGHT, 123),
            Line("გამწყდარიყო", LEFT, 124, 95, 135),
        ],
    )
    paragraphs = [flush("თავი მესამე", 100), title, text("იმავე წლის ოქტომბრის ბოლოს.", 161)]
    [section] = build_sections(paragraphs, PAGES)
    assert section.heading == Heading(1, "თავი მესამე", title.text)
    assert [p.text for p in section.paragraphs] == ["იმავე წლის ოქტომბრის ბოლოს."]


def test_heading_set_in_the_text_is_a_section_below_the_chapter() -> None:
    restaurant = flush("რესტორანში", 200)
    restaurant.apart = True
    paragraphs = [
        flush("თავი პირველი", 100),
        flush("ჩამოსვლა", 112),
        text("ერთი უბრალო ყმაწვილი კაცი.", 140),
        restaurant,
        text("ნათელი, მყუდრო რესტორანი.", 212),
    ]
    assert headings(paragraphs) == [
        Heading(1, "თავი პირველი", "ჩამოსვლა"),
        Heading(2, "რესტორანში"),
    ]


def test_sentence_set_apart_is_not_a_heading() -> None:
    sentence = flush("კარი გაიღო.", 200)
    sentence.apart = True
    paragraphs = [flush("თავი პირველი", 100), text("ტექსტი.", 140), sentence, text("მერე.", 212)]
    assert headings(paragraphs) == [Heading(1, "თავი პირველი")]
