import re

from pdf2epub.paragraphs import Paragraph
from pdf2epub.pdf import OutlineEntry

from .notes import TITLES as NOTES_TITLES

# The outline is trusted when at least this many of its entries, and this share of
# them, are headings printed on the page they point to; else the text is read alone.
MIN_MATCHED = 3
MIN_SHARE = 0.6

# A title may wrap over this many paragraphs: "ახალმეტყველების" / "პრინციპები".
MAX_TITLE_PARAGRAPHS = 3

NOT_WORD = re.compile(r"[\W_]+")


def outline_headings(
    paragraphs: list[Paragraph], outline: list[OutlineEntry]
) -> dict[int, tuple[int, int]] | None:
    """The paragraphs the PDF's outline names as headings, in order: the index of each
    one's first paragraph, with its level and how many paragraphs it takes. None if the
    outline doesn't fit the text. Notes are left to be found as notes."""
    entries = [e for e in outline if key(e.title) and key(e.title) not in NOTES_TITLES]
    found: dict[int, tuple[int, int]] = {}
    start = 0
    for entry in entries:
        want = key(entry.title)
        for index in range(start, len(paragraphs)):
            page = paragraphs[index].page
            if page > entry.page + 1:
                break
            if page >= entry.page and (span := title_span(paragraphs, index, want)):
                found[index] = (entry.level, span)
                start = index + span
                break
    if len(found) < max(MIN_MATCHED, MIN_SHARE * len(entries)):
        return None
    return found


def title_span(paragraphs: list[Paragraph], index: int, want: str) -> int:
    """How many paragraphs from `index` on spell the title, 0 if they don't."""
    text = ""
    for count, paragraph in enumerate(paragraphs[index : index + MAX_TITLE_PARAGRAPHS], 1):
        text = f"{text} {key(paragraph.text)}".strip()
        if text == want:
            return count
        if not want.startswith(text):
            return 0
    return 0


def key(text: str) -> str:
    """The words alone, to compare: ".: I :." and "i" match."""
    return NOT_WORD.sub(" ", text).strip().casefold()
