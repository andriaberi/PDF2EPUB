import pytest

from bookflow.pdf.models import Line, Page
from bookflow.pdf.noise import is_junk, is_page_number, remove_noise


def page(number: int, *rows: tuple[float, str]) -> Page:
    return Page(number, 400, 600, [Line(text, 50, y, 350, y + 10) for y, text in rows])


@pytest.mark.parametrize(
    "text",
    ["2 72<2C 2", "VILI0L I0IVთ0", "L08 M198M046ცL1X8", "| (8 L ს 42:52 C2.", "/”(."],
)
def test_ocr_junk(text: str) -> None:
    assert is_junk(text)


@pytest.mark.parametrize(
    "text",
    [
        "1815 წელს შარლ-ფრანსუა-ბიენვენიუ. მირიელი",
        "The quick brown fox.",
        "* * *",
        "IV",
        "1963",
    ],
)
def test_real_text(text: str) -> None:
    assert not is_junk(text)


@pytest.mark.parametrize("text", ["12", "- 12 -", "xiv", "1,", "9276"])
def test_page_numbers(text: str) -> None:
    assert is_page_number(text)


@pytest.mark.parametrize("text", ["The End", "დასასრული", "XI", "I", "IV."])
def test_not_page_numbers(text: str) -> None:
    assert not is_page_number(text)


def test_removes_page_numbers_at_the_bottom() -> None:
    [result] = remove_noise([page(1, (100, "Some text here."), (570, "21"))])
    assert [line.text for line in result.lines] == ["Some text here."]


def test_keeps_numbers_in_the_body() -> None:
    [result] = remove_noise([page(1, (100, "Some text here."), (300, "1815"), (400, "More."))])
    assert [line.text for line in result.lines] == ["Some text here.", "1815", "More."]


@pytest.mark.parametrize("text", ["ეს ფასტი.[2]", "à კიტის.[40]", "Lady“.[54]"])
def test_a_note_mark_doesnt_make_a_line_junk(text: str) -> None:
    assert not is_junk(text)


def test_removes_running_headers() -> None:
    pages = [page(n, (20, f"Les Misérables {n}"), (100, f"Text {n}.")) for n in range(1, 5)]
    assert [[line.text for line in p.lines] for p in remove_noise(pages)] == [
        ["Text 1."],
        ["Text 2."],
        ["Text 3."],
        ["Text 4."],
    ]


def test_keeps_chapter_numbers_at_the_top_of_pages() -> None:
    # Each part has its own chapter VII: it repeats like a header, but it is a heading.
    pages = [page(n, (20, "VII"), (100, f"Text {n}.")) for n in range(1, 5)]
    first = remove_noise(pages)[0]
    assert [line.text for line in first.lines] == ["VII", "Text 1."]


def test_keeps_a_label_repeated_across_the_book() -> None:
    # Every book of a novel has its chapter three, at the top of some page.
    pages = [page(n, (100, f"Text {n}.")) for n in range(1, 10)]
    for number in (2, 5, 8):
        pages[number - 1].lines.insert(0, Line("თავი მესამე", 50, 20, 100, 30))
    assert [line.text for line in remove_noise(pages)[4].lines] == ["თავი მესამე", "Text 5."]


def test_removes_a_label_running_as_a_header() -> None:
    pages = [page(n, (20, "Chapter Three"), (100, f"Text {n}.")) for n in range(1, 5)]
    assert [line.text for line in remove_noise(pages)[1].lines] == ["Text 2."]


def test_removes_page_number_glued_to_text() -> None:
    pages = [page(n, (100, "Text."), (570, str(n + 1))) for n in range(1, 5)]
    pages.append(page(5, (100, "Text."), (560, "the last line. 6")))
    assert [line.text for line in remove_noise(pages)[-1].lines] == ["Text.", "the last line."]


def test_clears_pages_without_a_real_word() -> None:
    [result] = remove_noise([page(1, (100, "I III"), (200, "M"))])
    assert result.lines == []


def test_strips_debris_but_keeps_footnote_marks() -> None:
    p = body(1, 30, (500, "' ვ. ი ლენინი, თხზულებანი."))
    p.lines.insert(0, Line("' ლივრი", 50, 80, 350, 90))
    [result] = remove_noise([p])
    assert result.lines[0].text == "ლივრი"
    assert texts(result.footnotes) == ["' ვ. ი ლენინი, თხზულებანი."]


def test_clears_junk_heavy_pages() -> None:
    [result] = remove_noise(
        [page(1, (100, "#22222X”>I>2."), (150, "72<2C"), (200, "M"), (300, "საქართველო"))]
    )
    assert [line.text for line in result.lines] == ["საქართველო"]


def body(number: int, rows: int, *extra: tuple[float, str]) -> Page:
    """A page of ordinary text lines 12 apart (2 of gap), followed by the extra lines."""
    lines = [(100 + 12 * row, f"Body text line {row}.") for row in range(rows)]
    return page(number, *lines, *extra)


def texts(lines: list[Line]) -> list[str]:
    return [line.text for line in lines]


def test_moves_footnotes_to_their_own_list() -> None:
    p = body(1, 30, (500, "'! კ. მარქსი და ფ. ენგელსი, გვ. 447."), (513, "31 მორის ტორეზი."))
    [result] = remove_noise([p])
    assert texts(result.footnotes) == ["'! კ. მარქსი და ფ. ენგელსი, გვ. 447.", "31 მორის ტორეზი."]
    assert texts(result.lines)[-1] == "Body text line 29."


def test_keeps_a_last_line_without_a_mark() -> None:
    [result] = remove_noise([body(1, 30, (500, "The end of the chapter."))])
    assert result.footnotes == []
    assert texts(result.lines)[-1] == "The end of the chapter."


def test_keeps_a_marked_line_without_a_gap() -> None:
    [result] = remove_noise([body(1, 30, (460, "1 more line of the body."))])
    assert result.footnotes == []


def test_keeps_a_section_that_runs_on_to_the_next_page() -> None:
    [result] = remove_noise([body(1, 30, (500, "1. A numbered section that goes on-"))])
    assert result.footnotes == []


def test_keeps_dialogue_after_a_gap() -> None:
    [result] = remove_noise([body(1, 30, (500, "— ვინ არის ეს პატარა კაცი?"))])
    assert result.footnotes == []
