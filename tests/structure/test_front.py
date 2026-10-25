from pdf2epub.paragraphs import Paragraph
from pdf2epub.pdf import Line
from pdf2epub.structure import Heading, Section
from pdf2epub.structure.front import (
    drop_front_matter,
    drop_prefaces,
    drop_repeated_title,
    drop_text_before_first_heading,
    drop_title_page_reprints,
    parts,
    title_page_spelling,
)


def test_front_matter_repeating_the_title_is_dropped() -> None:
    title, author = "Les Misérables", "Victor Hugo"
    front = Section(None, [Paragraph("Victor Hugo", 1), Paragraph("LES MISÉRABLES", 1)])
    chapter = Section(Heading(1, "Chapter 1"), [Paragraph("Text.", 2)])
    assert drop_repeated_title([front, chapter], title, author) == [chapter]


def test_front_matter_with_more_is_kept() -> None:
    title, author = "Les Misérables", None
    front = Section(None, [Paragraph("Les Misérables", 1), Paragraph("A preface.", 1)])
    [kept] = drop_repeated_title([front], title, author)
    assert [p.text for p in kept.paragraphs] == ["A preface."]


def test_title_page_is_dropped_without_the_title_in_metadata() -> None:
    title, author = "ucxo", None
    front = Section(None, [Paragraph("ალბერ კამიუ - უცხო", 1)])
    part = Section(Heading(1, "ნაწილი პირველი"))
    assert drop_repeated_title([front, part], title, author) == [part]


def test_text_before_the_first_heading_is_dropped() -> None:
    front = Section(
        None,
        [
            Paragraph("ლევ ტოლსტოი", 1),
            Paragraph("ლარისა ტიტვინიძისა და თამარ საყვარელიძის თარგმანი", 1),
            Paragraph("ჩემი არს შურისგება, და მე მივაგო.", 1),
        ],
    )
    part = Section(Heading(1, "ნაწილი პირველი"), [Paragraph(f"ტექსტი {n}.", 2) for n in range(40)])
    assert drop_text_before_first_heading([front, part]) == [part]


def test_a_book_without_headings_keeps_its_text() -> None:
    only = Section(None, [Paragraph("ტექსტი.", 1)])
    assert drop_text_before_first_heading([only]) == [only]


def test_long_text_before_the_first_heading_is_kept() -> None:
    # A tenth of the book or more: the first chapters, their headings missed.
    front = Section(None, [Paragraph(f"ტექსტი {n}.", 1) for n in range(20)])
    chapter = Section(Heading(1, "თავი მეორე"), [Paragraph(f"ტექსტი {n}.", 9) for n in range(40)])
    assert drop_text_before_first_heading([front, chapter]) == [front, chapter]


def test_title_page_printed_again_before_a_volume_is_dropped() -> None:
    front = Section(None, [Paragraph("ომი და მშვიდობა", 1)])
    chapter = Section(Heading(3, "თავი ოცდამეერთე"), [Paragraph("ტექსტი.", 2)])
    chapter.paragraphs.append(Paragraph("ომი და მშვიდობა", 3))
    volume = Section(Heading(1, "ტომი II"))
    drop_title_page_reprints([front, chapter, volume])
    assert [p.text for p in chapter.paragraphs] == ["ტექსტი."]


def test_reprint_without_the_dot_leaders_is_dropped() -> None:
    front = Section(None, [Paragraph("ლევ ტოლსტოი", 1), Paragraph("თამარის თარგმანი. . .. . .", 1)])
    chapter = Section(Heading(3, "XXIII"), [Paragraph("ტექსტი.", 2)])
    chapter.paragraphs += [Paragraph("ლევ ტოლსტოი", 9), Paragraph("თამარის თარგმანი", 9)]
    drop_title_page_reprints([front, chapter, Section(Heading(1, "ნაწილი მეხუთე"))])
    assert [p.text for p in chapter.paragraphs] == ["ტექსტი."]


def test_title_page_reprinted_for_the_next_volume_is_dropped() -> None:
    front = Section(
        None,
        [
            Paragraph("ლევ ტოლსტოი", 1),
            Paragraph("ანა კარენინა (ტომი I)", 1),
            Paragraph("თარგმანი", 1),
            Paragraph("ჩემი არს შურისგება, და მე მივაგო.", 1),
        ],
    )
    chapter = Section(Heading(2, "XXIII"), [Paragraph("ტექსტი.", 2)])
    chapter.paragraphs += [Paragraph(text, 3) for text in ("ლევ ტოლსტოი", "ანა კარენინა (ტომი II)")]
    drop_title_page_reprints([front, chapter])
    assert [p.text for p in chapter.paragraphs] == ["ტექსტი."]


def test_metadata_in_latin_is_spelled_as_the_title_page_does() -> None:
    front = Section(None, [Paragraph("ლევ ტოლსტოი", 1), Paragraph("ანა კარენინა (ტომი I)", 1)])
    sections = [front, Section(Heading(1, "ნაწილი პირველი"))]
    assert title_page_spelling(sections, "Ana karenina II", "Leo Tolstoy") == (
        "ანა კარენინა",
        "ლევ ტოლსტოი",
    )


def test_metadata_without_a_matching_line_is_kept() -> None:
    sections = [Section(None, [Paragraph("ალბერ კამიუ - უცხო", 1)])]
    assert title_page_spelling(sections, "Henry V", None) == ("Henry V", None)


def test_prefaces_are_dropped_with_their_sections() -> None:
    preface = Section(Heading(1, "წინასიტყვაობა"), [Paragraph("Text.", 1)])
    inside = Section(Heading(2, "I"), [Paragraph("Text.", 2)])
    part = Section(Heading(1, "ნაწილი პირველი"), [Paragraph("Text.", 3)])
    chapter = Section(Heading(2, "თავი პირველი"), [Paragraph("Text.", 3)])
    assert drop_prefaces([preface, inside, part, chapter]) == [part, chapter]


def test_prologue_is_kept() -> None:
    prologue = Section(Heading(1, "პროლოგი"), [Paragraph("Text.", 1)])
    assert drop_prefaces([prologue]) == [prologue]


def test_what_is_left_out_is_marked_with_its_role() -> None:
    front = Section(
        None,
        [
            Paragraph("Victor Hugo", 1),
            Paragraph("Les Misérables", 1),
            Paragraph("Translated by someone.", 1),
        ],
    )
    preface = Section(Heading(1, "Preface"), [Paragraph("Why I wrote it.", 2)])
    chapter = Section(
        Heading(1, "Chapter 1"),
        [*(Paragraph(f"Text {n}.", 3) for n in range(40)), Paragraph("Les Misérables", 9)],
    )
    everything = parts([front, preface, chapter])
    assert drop_front_matter([front, preface, chapter], "Les Misérables", "Victor Hugo") == [
        chapter
    ]
    assert [
        (part.label if isinstance(part, Heading) else part.text, part.role)
        for part in everything
        if part.role != "body"
    ] == [
        ("Victor Hugo", "title-page"),
        ("Les Misérables", "title-page"),
        ("Translated by someone.", "front"),
        ("Preface", "preface"),
        ("Why I wrote it.", "preface"),
        ("Les Misérables", "reprint"),
    ]


def one_line(text: str, x0: float = 85, page: int = 65) -> Paragraph:
    return Paragraph(text, page, [Line(text, x0, 100, 500, 112)])


def test_colophon_after_the_last_line_is_left_out() -> None:
    text = [one_line(f"სიტყვა {n}.") for n in range(5)]
    colophon = [
        one_line("ნოემბერი 1943 - თებერვალი 1944."),
        one_line("გამომცემლობა „გულანი“", x0=384),
        one_line("ინგლისურიდან თარგმნა - მზია კეკელიძემ", x0=318),
    ]
    chapter = Section(Heading(1, "თავი X"), [*text, *colophon])
    drop_front_matter([chapter], "ცხოველების ფერმა", None)
    assert chapter.paragraphs == text
    assert [p.role for p in colophon] == ["back"] * 3


def test_last_line_of_the_text_stays() -> None:
    text = [one_line(f"სიტყვა {n}.") for n in range(5)]
    chapter = Section(Heading(1, "თავი X"), [*text, one_line("[3] შენიშვნა 1943 წლისა.")])
    drop_front_matter([chapter], "ცხოველების ფერმა", None)
    assert len(chapter.paragraphs) == 6
