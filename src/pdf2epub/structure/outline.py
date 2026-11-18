import re
from dataclasses import dataclass

from pdf2epub.labels import NUMBER_LEVEL, label_level, numeral_value
from pdf2epub.paragraphs import Paragraph
from pdf2epub.pdf import OutlineEntry

from .models import Heading
from .notes import TITLES as NOTES_TITLES

MIN_MATCHED = 3
MIN_SHARE = 0.6
MAX_TITLE_PARAGRAPHS = 3
SEPARATOR = re.compile(r"\s+[-–—]\s+")
NOT_WORD = re.compile(r"[\W_]+")
SCENE_MARKS = " *⁂•·~="


@dataclass
class Match:
    entry: OutlineEntry
    span: int
    line: int = 0


def outline_headings(
    paragraphs: list[Paragraph], outline: list[OutlineEntry]
) -> dict[int, Match] | None:
    entries = [e for e in outline if key(e.title) and key(e.title) not in NOTES_TITLES]
    found: dict[int, Match] = {}
    start = 0
    for entry in entries:
        want = key(entry.title)
        for index in range(start, len(paragraphs)):
            page = paragraphs[index].page
            if page > entry.page + 1:
                break
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
    if len(paragraph.lines) < 2:
        return None
    return next((n for n, line in enumerate(paragraph.lines) if key(line.text) == want), None)


def title_span(paragraphs: list[Paragraph], index: int, want: str) -> int | None:
    text = ""
    for count, paragraph in enumerate(paragraphs[index : index + MAX_TITLE_PARAGRAPHS], 1):
        text = f"{text} {key(paragraph.text)}".strip()
        if text == want:
            return count
        if not want.startswith(text):
            return None
    return None


def entry_headings(printed: str, entry: OutlineEntry, flat: bool) -> list[Heading]:
    printed = printed.strip(SCENE_MARKS)
    parts = SEPARATOR.split(printed)
    if sum(1 for part in parts if is_label_or_number(part)) < 2:
        parts = [printed]
    headings: list[Heading] = []
    for part in parts:
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
    return NOT_WORD.sub(" ", text).strip().casefold()
