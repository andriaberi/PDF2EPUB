import re
from dataclasses import dataclass

from pdf2epub.labels import NUMBER_LEVEL, label_level, numeral_value
from pdf2epub.paragraphs import Paragraph
from pdf2epub.pdf import OutlineEntry

from .models import Heading
from .notes import TITLES as NOTES_TITLES

# The outline is trusted when at least this many of its entries, and this share of
# them, are headings printed on the page they point to; else the text is read alone.
MIN_MATCHED = 3
MIN_SHARE = 0.6

# A title may wrap over this many paragraphs: "ახალმეტყველების" / "პრინციპები".
MAX_TITLE_PARAGRAPHS = 3

# Some outlines run a part, its chapter and the chapter's first section into one
# entry: "ნაწილი პირველი - თავი პირველი - I".
SEPARATOR = re.compile(r"\s+[-–—]\s+")

NOT_WORD = re.compile(r"[\W_]+")

SCENE_MARKS = " *⁂•·~="


@dataclass
class Match:
    entry: OutlineEntry
    # How many paragraphs the title takes; 0 when it is only a line of one, set in the
    # text's size and run together with the text around it.
    span: int
    line: int = 0  # which line, then


def outline_headings(
    paragraphs: list[Paragraph], outline: list[OutlineEntry]
) -> dict[int, Match] | None:
    """The paragraphs the PDF's outline names as headings, in order, by the index of
    each one's first paragraph. None if the outline doesn't fit the text. Notes are
    left to be found as notes."""
    entries = [e for e in outline if key(e.title) and key(e.title) not in NOTES_TITLES]
    found: dict[int, Match] = {}
    start = 0
    for entry in entries:
        want = key(entry.title)
        for index in range(start, len(paragraphs)):
            page = paragraphs[index].page
            if page > entry.page + 1:
                break
            # A title run into the text may be in a paragraph begun the page before.
            if page < entry.page - 1:
                continue
            if (line := title_line(paragraphs[index], want)) is not None:
                found[index] = Match(entry, 0, line)
                start = index + 1
                break
            if page >= entry.page and (span := title_span(paragraphs, index, want)) is not None:
                found[index] = Match(entry, span)
                start = index + span
                break
    if len(found) < max(MIN_MATCHED, MIN_SHARE * len(entries)):
        return None
    return found


def title_line(paragraph: Paragraph, want: str) -> int | None:
    """Which line of a paragraph of several is the title, if one is."""
    if len(paragraph.lines) < 2:
        return None
    return next((n for n, line in enumerate(paragraph.lines) if key(line.text) == want), None)


def title_span(paragraphs: list[Paragraph], index: int, want: str) -> int | None:
    """How many paragraphs from `index` on spell the title, None if they don't."""
    text = ""
    for count, paragraph in enumerate(paragraphs[index : index + MAX_TITLE_PARAGRAPHS], 1):
        text = f"{text} {key(paragraph.text)}".strip()
        if text == want:
            return count
        if not want.startswith(text):
            return None
    return None


def entry_headings(printed: str, entry: OutlineEntry, flat: bool) -> list[Heading]:
    """The headings an entry names, as printed: one, or a part, its chapter and the
    chapter's first section from a combined entry, nested. In a flat outline, where
    every entry has the same level, each takes the level of its label word."""
    # A scene break set just above a heading may have run into it: "* * * მეშვიდე ნაწილი".
    printed = printed.strip(SCENE_MARKS)
    parts = SEPARATOR.split(printed)
    if sum(1 for part in parts if is_label_or_number(part)) < 2:
        parts = [printed]
    headings: list[Heading] = []
    for part in parts:
        # A name between labels is the title of the one before: "თავი მეცამეტე - დასასრული".
        if headings and not is_label_or_number(part):
            last = headings[-1]
            last.title = f"{last.title} - {part}" if last.title else part
            continue
        level = entry.level + len(headings)
        if flat:
            numbered = NUMBER_LEVEL if numeral_value(part) is not None else entry.level
            level = label_level(part) or numbered
        headings.append(Heading(level, part))
    return headings


def is_label_or_number(text: str) -> bool:
    return label_level(text) is not None or numeral_value(text) is not None


def key(text: str) -> str:
    """The words alone, to compare: ".: I :." and "i" match."""
    return NOT_WORD.sub(" ", text).strip().casefold()
