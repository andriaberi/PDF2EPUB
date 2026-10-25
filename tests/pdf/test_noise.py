import pytest

from pdf2epub.pdf.models import Footnote, Line, Page
from pdf2epub.pdf.noise import drop_web_credits, is_junk, is_page_number, remove_noise


def page(number: int, *rows: tuple[float, str], scanned: bool = True) -> Page:
    lines = [Line(text, 50, y, 350, y + 10) for y, text in rows]
    return Page(number, 400, 600, lines, scanned=scanned)


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
        # A note's mark glued to a word leaves it a word.
        "ეს ფასტი.[2]",
        "à კიტის.[40]",
        "Lady“.[54]",
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
    assert texts(result.lines)[0] == "ლივრი"
    assert texts(result.lines)[-1] == "Body text line 29."


def test_clears_junk_heavy_pages() -> None:
    [result] = remove_noise(
        [page(1, (100, "#22222X”>I>2."), (150, "72<2C"), (200, "M"), (300, "საქართველო"))]
    )
    assert [line.text for line in result.lines] == ["საქართველო"]


def test_keeps_odd_lines_of_a_born_digital_page() -> None:
    # Only OCR makes junk: a printed page's "#34" or "A" is a heading, "!" a line's end.
    rows = [(100, "#34"), (120, "A"), (140, "Lise-მაც ამოიოხრა."), (160, "!"), (180, "' ლივრი")]
    [result] = remove_noise([page(1, *rows, scanned=False)])
    assert texts(result.lines) == ["#34", "A", "Lise-მაც ამოიოხრა.", "!", "' ლივრი"]


def body(number: int, rows: int, *extra: tuple[float, str]) -> Page:
    """A page of ordinary text lines 12 apart (2 of gap), followed by the extra lines."""
    lines = [(100 + 12 * row, f"Body text line {row}.") for row in range(rows)]
    return page(number, *lines, *extra)


def texts(lines: list[Line]) -> list[str]:
    return [line.text for line in lines]


def test_drops_footnotes() -> None:
    p = body(1, 30, (500, "'! კ. მარქსი და ფ. ენგელსი, გვ. 447."), (513, "31 მორის ტორეზი."))
    [result] = remove_noise([p])
    assert texts(result.lines)[-1] == "Body text line 29."


def test_keeps_a_last_line_without_a_mark() -> None:
    [result] = remove_noise([body(1, 30, (500, "The end of the chapter."))])
    assert texts(result.lines)[-1] == "The end of the chapter."


def test_keeps_a_marked_line_without_a_gap() -> None:
    [result] = remove_noise([body(1, 30, (460, "1 more line of the body."))])
    assert texts(result.lines)[-1] == "1 more line of the body."


def test_keeps_a_section_that_runs_on_to_the_next_page() -> None:
    [result] = remove_noise([body(1, 30, (500, "1. A numbered section that goes on-"))])
    assert texts(result.lines)[-1] == "1. A numbered section that goes on-"


def test_keeps_dialogue_after_a_gap() -> None:
    [result] = remove_noise([body(1, 30, (500, "— ვინ არის ეს პატარა კაცი?"))])
    assert texts(result.lines)[-1] == "— ვინ არის ეს პატარა კაცი?"


def test_credits_stacked_flush_left_are_dropped_too() -> None:
    lines = [
        Line("სიგარეტიდან თამბაქო ძირს დაცვივდა.", 5, 338, 400, 352),
        Line("წიგნის ელექტრონული ვერსია", 309, 513, 520, 530),
        Line("მოამზადა საიტმა: www.ChiaturaINFO.GE", 309, 541, 600, 558),
    ]
    assert [line.text for line in drop_web_credits(lines)] == [lines[0].text]


def test_a_line_naming_the_website_is_a_credit() -> None:
    lines = [Line("[11] პროპაგანდისტი (მთარ.).", 5, 530, 300, 547)]
    lines.append(Line(".:სასიყვარულო საიტი:.", 150, 711, 330, 728))
    assert [line.text for line in drop_web_credits(lines)] == [lines[0].text]


def test_website_credits_are_dropped_with_the_lines_above_them() -> None:
    lines = [
        Line("დასასრული.", 485, 365, 556, 380),
        Line("წიგნის ელექტრონული ვერსია", 363, 412, 559, 430),
        Line("მოამზადა: აკაკი ციცქიშვილმა", 366, 440, 559, 458),
        Line("www.ChiaturaINFO.GE", 419, 469, 559, 483),
    ]
    assert [line.text for line in drop_web_credits(lines)] == ["დასასრული."]


def test_keeps_a_parts_heading_under_its_running_header() -> None:
    pages = [page(n, (20, "მეორე ნაწილი"), (100, f"Text {n}.")) for n in range(1, 5)]
    pages[0].lines.insert(1, Line("მეორე ნაწილი", 120, 40, 280, 56))
    assert texts(remove_noise(pages)[0].lines) == ["მეორე ნაწილი", "Text 1."]


def test_keeps_a_heading_opening_with_a_label_repeated_across_the_book() -> None:
    pages = [page(n, (100, f"Text {n}.")) for n in range(1, 10)]
    for number in (2, 5, 8):
        pages[number - 1].lines.insert(0, Line("თავი მეორე - I", 50, 20, 150, 30))
    assert texts(remove_noise(pages)[4].lines) == ["თავი მეორე - I", "Text 5."]


def test_footnote_with_a_raised_mark_is_kept_and_linked() -> None:
    p = body(1, 30, (500, "79ფილტვების ანთება (ლათ.)."))
    p.scanned = False
    p.lines[3].text = "დიახ, pneumonia⁅79⁆ გახლავთ."
    [result] = remove_noise([p])
    assert result.footnotes == [Footnote("1", "ფილტვების ანთება (ლათ.).")]
    assert result.lines[3].text == "დიახ, pneumonia[1] გახლავთ."
    assert texts(result.lines)[-1] == "Body text line 29."


def test_footnotes_numbered_from_1_on_each_page_are_numbered_through() -> None:
    pages = [body(n, 30, (500, "1 შენიშვნა.")) for n in (1, 2)]
    for p in pages:
        p.scanned = False
        p.lines[0].text = "სიტყვა⁅1⁆."
    result = remove_noise(pages)
    assert [p.lines[0].text for p in result] == ["სიტყვა[1].", "სიტყვა[2]."]
    assert [f.mark for p in result for f in p.footnotes] == ["1", "2"]


def test_raised_mark_without_its_footnote_is_taken_out() -> None:
    p = body(1, 30)
    p.scanned = False
    p.lines[0].text = "სიტყვა⁅5⁆ და სხვა."
    assert remove_noise([p])[0].lines[0].text == "სიტყვა და სხვა."


def test_footnote_under_a_page_of_short_dialogue() -> None:
    # Most gaps are the wide ones between one-line paragraphs; the narrow ones between
    # a paragraph's lines tell the usual gap, so the footnote's gap still stands out.
    rows, y = [], 100.0
    for n in range(18):
        rows.append((y, f"— ტექსტი {n}."))
        y += 12 if n % 3 == 2 else 30
    p = page(1, *rows, (rows[-1][0] + 40, "1 შენიშვნა."), scanned=False)
    p.lines[0].text = "— ტექსტი⁅1⁆."
    assert [f.text for f in remove_noise([p])[0].footnotes] == ["შენიშვნა."]
