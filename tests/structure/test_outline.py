from pdf2epub.paragraphs import Paragraph
from pdf2epub.pdf import OutlineEntry
from pdf2epub.structure.outline import outline_headings

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
    assert outline_headings(TEXT, outline) == {
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
    assert outline_headings(TEXT, outline) == {0: (1, 1), 1: (2, 1), 3: (2, 1)}
