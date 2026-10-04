from bookflow.labels import NUMBER_LEVEL, find_label, fix_label, label_level, numeral_value
from bookflow.paragraphs import Paragraph
from bookflow.paragraphs.builder import join
from bookflow.paragraphs.layout import Layout, is_tall, text_column
from bookflow.pdf import Page

from .headings import (
    MAX_TITLE_LINES,
    gap_after,
    is_centred,
    is_label,
    is_short,
    is_title,
)
from .models import Heading, Section

# Lone numbers count as chapter numbers only when the book has at least this many.
MIN_NUMBERED = 3

# A number may skip this many: OCR loses one now and then.
MAX_SKIP = 2


def build_sections(paragraphs: list[Paragraph], pages: list[Page]) -> list[Section]:
    """Split the paragraphs at chapter (and part, book) headings."""
    column = text_column(pages)
    numbered = numbered_chapters(paragraphs)
    sections = [Section(heading=None)]

    index = 0
    while index < len(paragraphs):
        paragraph = paragraphs[index]
        index += 1
        if is_label(paragraph, column):
            heading = Heading(label_level(paragraph.text) or 0, fix_label(paragraph.text))
        elif id(paragraph) in numbered:
            heading = Heading(NUMBER_LEVEL, paragraph.text.rstrip("."))
        else:
            sections[-1].paragraphs.append(paragraph)
            continue

        # A label in a bigger font than the text has its title in one too; a line in
        # the text's size after it is the chapter's first line, and it has no title.
        tall = is_tall(paragraph.lines[0], column)
        # A title can wrap onto more centred lines, each read as a paragraph of its own.
        title: list[Paragraph] = []
        while index < len(paragraphs) and is_title_part(paragraphs[index], title, column, tall):
            title.append(paragraphs[index])
            index += 1
        # Short paragraphs after a label set flush left may be text, not title: a title
        # is set off from the text below it, so drop parts until one is.
        while title and not is_set_off(title, paragraphs[index : index + 1], column):
            title.pop()
            index -= 1
        following = paragraphs[index] if index < len(paragraphs) else None
        if title:
            heading.title = " ".join(part.text for part in title)
        elif following and not tall and (split := split_title(following, column)):
            heading.title, paragraphs[index] = split
        sections.append(Section(heading))

    if not sections[0].paragraphs:
        sections.pop(0)
    renumber_levels(sections)
    match_label_order(sections)
    return sections


def numbered_chapters(paragraphs: list[Paragraph]) -> set[int]:
    """The lone numbers that number the book's chapters ("I", "II", ... or "1.", "2.").

    They count up through the book and may start again at 1 in each part; a number
    out of step, like a stray "7" in the text, isn't a chapter. Gives paragraph ids.
    """
    found: set[int] = set()
    last: int | None = None
    for paragraph in paragraphs:
        value = numeral_value(paragraph.text) if len(paragraph.lines) == 1 else None
        if value is None:
            continue
        if last is None or value == 1 or 0 < value - last <= MAX_SKIP:
            found.add(id(paragraph))
            last = value
    return found if len(found) >= MIN_NUMBERED else set()


def is_set_off(title: list[Paragraph], following: list[Paragraph], column: Layout) -> bool:
    centred = all(is_centred(line, column) for part in title for line in part.lines)
    return centred or gap_after(title[-1], following[0] if following else None, column)


def split_title(paragraph: Paragraph, column: Layout) -> tuple[str, Paragraph] | None:
    """A title run into the text after it, as across a page break.

    In justified text only a paragraph's last line is short, so a short first line
    followed by more lines is a title.
    """
    first, *rest = paragraph.lines
    if not rest or not is_short(first, column) or first.text.endswith((".", ",", ";", ":")):
        return None
    text = rest[0].text
    for line in rest[1:]:
        text = join(text, line.text)
    return first.text, Paragraph(text, paragraph.page, rest)


def is_title_part(paragraph: Paragraph, title: list[Paragraph], column: Layout, tall: bool) -> bool:
    lines = sum(len(part.lines) for part in title) + len(paragraph.lines)
    # "…ხელზე და უთხრა:" leads into speech, "– მოვიდნენ!" is speech and "…იწვა." ends a
    # sentence: titles do none of these, though they may ask ("სად მიდიან?") or trail off.
    text = paragraph.text
    return (
        lines <= MAX_TITLE_LINES
        and not text.endswith(":")
        and not (text.endswith(".") and not text.endswith(".."))
        and not text.startswith(("-", "–", "—"))
        and (not tall or all(is_tall(line, column) for line in paragraph.lines))
        and is_title(paragraph, column)
        and not is_label(paragraph, column)
        and numeral_value(paragraph.text) is None
        and (not title or paragraph.page == title[-1].page)
    )


def renumber_levels(sections: list[Section]) -> None:
    """Make the levels the book actually uses 1, 2, ... (a book of chapters is all 1)."""
    used = sorted({s.heading.level for s in sections if s.heading})
    for section in sections:
        if section.heading:
            section.heading.level = used.index(section.heading.level) + 1


def match_label_order(sections: list[Section]) -> None:
    """Put the label word where most of the book puts it.

    A book that mostly says "ნაწილი მეორე" may still print "მესამე ნაწილი"; the
    contents should read the same way throughout. Ties go to the label first.
    """
    headings = [s.heading for s in sections if s.heading and len(s.heading.label.split()) == 2]
    places = [found[0] for h in headings if (found := find_label(h.label))]
    second = places.count(1) > places.count(0)
    for heading in headings:
        found = find_label(heading.label)
        first, other = heading.label.split()
        # Only a word moves in front of the label: "Chapter 4" never becomes "4 Chapter".
        if found and found[0] != second and (not second or other.isalpha()):
            heading.label = f"{other} {first}"
