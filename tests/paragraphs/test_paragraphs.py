from bookflow.paragraphs import Paragraph, build_paragraphs
from bookflow.pdf import Line, Page

LEFT = 45.0
RIGHT = 385.0
INDENT = 62.0


def line(y: float, text: str, x0: float = LEFT, x1: float = RIGHT) -> Line:
    return Line(text, x0, y, x1, y + 10)


def page(number: int, *lines: Line) -> Page:
    return Page(number, 430, 590, list(lines))


def texts(pages: list[Page]) -> list[str]:
    return [paragraph.text for paragraph in build_paragraphs(pages)]


def test_joins_lines_with_spaces() -> None:
    p = page(1, line(100, "one two"), line(114, "three four"), line(128, "five.", x1=150))
    assert texts([p]) == ["one two three four five."]


def test_rejoins_hyphenated_words() -> None:
    p = page(1, line(100, "შვილი არ დარჩე-"), line(114, "ნია. როგორ", x1=150))
    assert texts([p]) == ["შვილი არ დარჩენია. როგორ"]


def test_keeps_hyphen_before_a_non_letter() -> None:
    p = page(1, line(100, "ten-"), line(114, "20 years", x1=150))
    assert texts([p]) == ["ten- 20 years"]


def test_indent_starts_a_paragraph() -> None:
    p = page(
        1,
        line(100, "First paragraph", x0=INDENT),
        line(114, "goes on here"),
        line(128, "Second paragraph", x0=INDENT),
        line(142, "goes on too"),
    )
    assert texts([p]) == ["First paragraph goes on here", "Second paragraph goes on too"]


def test_gap_starts_a_paragraph() -> None:
    p = page(1, line(60, "თავი პირველი", x0=170, x1=260), line(100, "ბატონი მირიელი"))
    assert texts([p]) == ["თავი პირველი", "ბატონი მირიელი"]


def test_line_in_a_bigger_font_stands_alone() -> None:
    p = page(
        1,
        Line("თავი მეორე", LEFT, 100, 120, 116),
        line(124, "ანა პავლოვნას სასტუმრო ოთახი"),
        line(138, "ხალხით ივსებოდა."),
    )
    assert texts([p]) == ["თავი მეორე", "ანა პავლოვნას სასტუმრო ოთახი ხალხით ივსებოდა."]


def test_short_line_ending_a_sentence_ends_the_paragraph() -> None:
    p = page(1, line(100, "It ended here.", x1=150), line(114, "A new one, indent lost."))
    assert texts([p]) == ["It ended here.", "A new one, indent lost."]


def test_continues_across_pages() -> None:
    first = page(1, line(100, "აქვე გარდაეცვალა ცოლი გუ-"))
    second = page(2, line(20, "ლის ავადმყოფობით."), line(34, "more text", x1=150))
    paragraphs = build_paragraphs([first, second])
    assert [p.text for p in paragraphs] == ["აქვე გარდაეცვალა ცოლი გულის ავადმყოფობით. more text"]
    assert paragraphs[0].page == 1


def test_new_page_after_finished_paragraph_starts_a_new_one() -> None:
    first = page(1, line(100, "Some text"), line(114, "The end.", x1=150))
    second = page(2, line(20, "Next one starts"), line(34, "here"))
    assert texts([first, second]) == ["Some text The end.", "Next one starts here"]


def test_hyphen_wins_over_indent() -> None:
    p = page(1, line(100, "მნიშვნე-"), line(114, "ლოვან მოვლენას", x0=INDENT))
    assert texts([p]) == ["მნიშვნელოვან მოვლენას"]


def test_skips_empty_pages() -> None:
    assert texts([page(1), page(2, line(100, "Text"))]) == ["Text"]


def test_page_ending_early_ends_the_paragraph() -> None:
    first = page(1, line(300, "თბილისი — 1963", x0=170, x1=260))
    second = page(2, line(300, "ფრანგულიდან თარგმნა", x0=170, x1=260))
    assert texts([first, second]) == ["თბილისი — 1963", "ფრანგულიდან თარგმნა"]


def full_page(number: int) -> Page:
    """Ordinary text, so the book's column can be measured."""
    return page(number, *(line(40 + 14 * row, "ტექსტი") for row in range(12)))


def verse_of(paragraphs: list[Paragraph]) -> list[list[str]]:
    return [[line.text for line in p.lines] for p in paragraphs if p.verse]


def test_verse_keeps_its_lines() -> None:
    p = page(
        2,
        line(100, "მერე ნიკოლაიმ იმღერა ჰანგი:", x1=200),
        line(124, "В приятну ночь, при лунном свете,", x1=200),
        line(138, "Представить счастливо себе,", x1=180),
        line(152, "Что некто есть еще на свете,", x1=190),
        line(166, "Кто думает и о тебе!", x1=150),
        line(190, "ტექსტი გრძელდება და გრძელდება"),
    )
    paragraphs = build_paragraphs([full_page(1), p])
    assert verse_of(paragraphs) == [
        [
            "В приятну ночь, при лунном свете,",
            "Представить счастливо себе,",
            "Что некто есть еще на свете,",
            "Кто думает и о тебе!",
        ]
    ]
    assert "მერე ნიკოლაიმ იმღერა ჰანგი:" in [p.text for p in paragraphs]


def test_wider_gap_parts_stanzas() -> None:
    lines = ["ერთი,", "ორი,", "სამი,", "ოთხი"]
    p = page(
        2,
        *(line(100 + 14 * row, text, x1=150) for row, text in enumerate(lines)),
        *(line(180 + 14 * row, text, x1=150) for row, text in enumerate(lines)),
    )
    assert verse_of(build_paragraphs([full_page(1), p])) == [lines, lines]


def test_short_sentences_are_not_verse() -> None:
    lines = ["მეორედ დააკაკუნა.", "ხმა შემოესმა.", "არავინაა.", "მესამედ დააკაკუნა."]
    p = page(2, *(line(100 + 14 * row, text, INDENT, 200) for row, text in enumerate(lines)))
    paragraphs = build_paragraphs([full_page(1), p])
    assert verse_of(paragraphs) == []
    assert [p.text for p in paragraphs[1:]] == lines


def test_dialogue_is_not_verse() -> None:
    lines = ["- ერთი,", "- ორი,", "- სამი,", "- ოთხი"]
    p = page(2, *(line(100 + 14 * row, text, INDENT, 150) for row, text in enumerate(lines)))
    assert verse_of(build_paragraphs([full_page(1), p])) == []


def test_page_of_short_lines_keeps_the_books_margins() -> None:
    # Measured alone, this page would take the indent for its margin and miss it.
    p = page(
        2,
        line(100, "ხელი მოაწერინა:", INDENT, 200),
        line(112, "„ბატონო ტენარდიე,", INDENT, 150),
        line(124, "ჩააბარეთ ჩემი კოზეტი.", INDENT, 200),
        line(136, "ფანტინი“.", INDENT, 120),
    )
    assert texts([full_page(1), p])[1:] == [
        "ხელი მოაწერინა:",
        "„ბატონო ტენარდიე,",
        "ჩააბარეთ ჩემი კოზეტი.",
        "ფანტინი“.",
    ]


def test_chapter_number_stands_alone() -> None:
    p = page(1, line(100, "XII", x1=80), line(114, "სტეპან არკადიჩი პირუთვნელი იყო."))
    assert texts([p]) == ["XII", "სტეპან არკადიჩი პირუთვნელი იყო."]


def test_text_right_after_a_label_starts_a_paragraph() -> None:
    p = page(1, line(100, "წინათქმა", x1=100), line(112, "ამ წიგნში ჰანს კასტორპის"))
    p.lines.append(line(124, "თავგადასავალი გვინდა გიამბოთ.", x1=200))
    assert texts([p]) == ["წინათქმა", "ამ წიგნში ჰანს კასტორპის თავგადასავალი გვინდა გიამბოთ."]


def test_line_of_text_starting_with_a_label_word_carries_on() -> None:
    p = page(
        1, line(100, "თავი მეორე სართულის ფანჯრიდან გადმოყო და"), line(112, "დაიძახა.", x1=100)
    )
    assert texts([p]) == ["თავი მეორე სართულის ფანჯრიდან გადმოყო და დაიძახა."]
