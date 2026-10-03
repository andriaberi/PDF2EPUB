from bookflow.paragraphs import build_paragraphs
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
