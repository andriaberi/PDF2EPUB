from pdf2epub.paragraphs import Paragraph
from pdf2epub.pdf import Line, OutlineEntry
from pdf2epub.structure.outline import entry_headings, outline_headings


def matched(paragraphs: list[Paragraph], outline: list[OutlineEntry]) -> dict[int, tuple[int, int]]:
    found = outline_headings(paragraphs, outline)
    assert found is not None
    return {index: (match.entry.level, match.span) for index, match in found.items()}


TEXT = [
    Paragraph("ერთი", 3),
    Paragraph("I", 3),
    Paragraph("აპრილის კაშკაშა, ცივი დღე იდგა.", 3),
    Paragraph("II", 15),
    Paragraph("ტექსტი.", 15),
    Paragraph("დასასრული", 201),
    Paragraph("ახალმეტყველების", 201),
    Paragraph("პრინციპები", 201),
    Paragraph("ტექსტი.", 201),
    Paragraph("სქოლიო", 211),
    Paragraph("[1] შენიშვნა.", 211),
]


def test_outline_entries_are_found_on_their_pages() -> None:
    outline = [
        OutlineEntry(1, "ერთი", 3),
        OutlineEntry(2, "I", 3),
        OutlineEntry(2, "II", 15),
        OutlineEntry(1, "დასასრული", 201),
        OutlineEntry(2, "ახალმეტყველების პრინციპები", 201),
        OutlineEntry(1, "სქოლიო", 211),
        OutlineEntry(1, "Blank Page", 1),
    ]
    assert matched(TEXT, outline) == {
        0: (1, 1),
        1: (2, 1),
        3: (2, 1),
        5: (1, 1),
        6: (2, 2),
    }


def test_outline_not_matching_the_text_is_not_used() -> None:
    outline = [OutlineEntry(1, f"Chapter {n}", n) for n in range(1, 6)]
    assert outline_headings(TEXT, outline) is None


def test_outline_too_short_to_trust_is_not_used() -> None:
    assert outline_headings(TEXT, [OutlineEntry(1, "ერთი", 3), OutlineEntry(2, "I", 3)]) is None


def test_entry_may_point_to_the_page_before_its_heading() -> None:
    outline = [OutlineEntry(1, "ერთი", 2), OutlineEntry(2, "I", 3), OutlineEntry(2, "II", 14)]
    assert matched(TEXT, outline) == {0: (1, 1), 1: (2, 1), 3: (2, 1)}


def test_combined_entry_in_a_flat_outline_is_nested_by_its_labels() -> None:
    entry = OutlineEntry(1, "ნაწილი პირველი - თავი პირველი - I", 2)
    headings = entry_headings(entry.title, entry, flat=True)
    assert [(h.level, h.label) for h in headings] == [
        (2, "ნაწილი პირველი"),
        (4, "თავი პირველი"),
        (5, "I"),
    ]


def test_name_between_labels_is_the_title_of_the_one_before() -> None:
    entry = OutlineEntry(1, "თავი მეცამეტე - დასასრული - I", 689)
    headings = entry_headings(entry.title, entry, flat=True)
    assert [h.text for h in headings] == ["თავი მეცამეტე: დასასრული", "I"]


def test_title_with_a_dash_stays_whole() -> None:
    entry = OutlineEntry(2, "ომი - მშვიდობა", 5)
    assert [h.text for h in entry_headings(entry.title, entry, flat=False)] == ["ომი - მშვიდობა"]


def test_scene_break_run_into_a_heading_is_left_off() -> None:
    entry = OutlineEntry(1, "მეშვიდე ნაწილი", 340)
    assert [h.label for h in entry_headings("* * * მეშვიდე ნაწილი", entry, flat=False)] == [
        "მეშვიდე ნაწილი"
    ]


def test_title_run_into_a_paragraph_begun_the_page_before() -> None:
    paragraphs = [
        Paragraph("ერთი", 1),
        Paragraph("ორი", 2),
        Paragraph("სამი", 3),
        Paragraph(
            "ტექსტი გრძელდება თავი მეორე - I ახალი თავი.",
            24,
            [line("ტექსტი გრძელდება"), line("თავი მეორე - I"), line("ახალი თავი.")],
        ),
    ]
    outline = [OutlineEntry(1, t, n) for n, t in ((1, "ერთი"), (2, "ორი"), (3, "სამი"))]
    found = outline_headings(paragraphs, [*outline, OutlineEntry(1, "თავი მეორე - I", 25)])
    assert found is not None
    assert (found[3].span, found[3].line) == (0, 1)


def line(text: str) -> Line:
    return Line(text, 0, 0, 100, 10)
