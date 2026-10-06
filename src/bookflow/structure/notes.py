import re

from bookflow.paragraphs import Paragraph

from .models import Note, Section

# Words the notes at the end of a book (or of a volume) are headed with.
TITLES = {"შენიშვნები", "notes", "endnotes"}

# A note's mark in the text, glued to the word it explains: "ფრეილინა[1]".
MARK = re.compile(r"\[(\d+)\]")

# A note starts with its mark and a space, at the start of a paragraph or after
# the last note: notes printed one under another often read as a single paragraph.
# Some PDFs keep a stray superscript after the mark: "[24]1 საამო ღამეს".
NOTE_START = re.compile(r"(?:^|(?<=\s))\[(\d+)\]\d*\s+")

# Notes without a title are known by their numbers: at least this many paragraphs in
# a row starting "[1] ", "[2] ", "[3] ".
MIN_UNTITLED_NOTES = 3


def extract_notes(sections: list[Section]) -> list[Note]:
    """Take the notes out of the text and link the marks in the text to them.

    A book may print notes at the end of each volume; the marks before a block of
    notes refer to that block, so numbering may start again after it.
    """
    notes: list[Note] = []
    waiting: list[Section] = []  # sections whose marks the next block of notes explains
    for section in sections:
        waiting.append(section)
        while (block := find_block(section.paragraphs)) is not None:
            start, first, end = block
            found = {
                mark: Note(f"note-{len(notes) + number}", mark, text)
                for number, (mark, text) in enumerate(
                    split_notes(section.paragraphs[first:end]), start=1
                )
            }
            notes.extend(found.values())
            del section.paragraphs[start:end]
            for marked in waiting:
                link_marks(marked, found)
            waiting = [section]
    return notes


def find_block(paragraphs: list[Paragraph]) -> tuple[int, int, int] | None:
    """Where a block of notes is, with its title if it has one: [start, end), the
    notes themselves from `first` on.

    A long note may go on in a paragraph of its own, so the notes reach the last
    paragraph that starts one.
    """
    for index, paragraph in enumerate(paragraphs):
        titled = (
            paragraph.text.strip().casefold() in TITLES
            and index + 1 < len(paragraphs)
            and NOTE_START.match(paragraphs[index + 1].text) is not None
        )
        if not titled and not starts_numbered_notes(paragraphs[index:]):
            continue
        first = index + 1 if titled else index
        starts = [
            number
            for number in range(first, len(paragraphs))
            if NOTE_START.match(paragraphs[number].text)
        ]
        return index, first, starts[-1] + 1
    return None


def starts_numbered_notes(paragraphs: list[Paragraph]) -> bool:
    """Notes printed without a title: "[1] ...", "[2] ...", "[3] ..." one under another."""
    wanted = [str(number) for number in range(1, MIN_UNTITLED_NOTES + 1)]
    marks = [NOTE_START.match(p.text) for p in paragraphs[:MIN_UNTITLED_NOTES]]
    return [match.group(1) if match else None for match in marks] == wanted


def split_notes(paragraphs: list[Paragraph]) -> list[tuple[str, str]]:
    """ "[1] ფრეილინა – ... [2] ლივრეანი – ..." as ("1", "ფრეილინა – ..."), ("2", ...)."""
    text = " ".join(paragraph.text for paragraph in paragraphs)
    starts = list(NOTE_START.finditer(text))
    return [
        (start.group(1), text[start.end() : following.start() if following else None].strip())
        for start, following in zip(starts, [*starts[1:], None], strict=True)
    ]


def link_marks(section: Section, notes: dict[str, Note]) -> None:
    """Record which notes the section's marks refer to, the first block's for each mark."""
    for paragraph in section.paragraphs:
        for mark in MARK.findall(paragraph.text):
            if mark in notes:
                section.notes.setdefault(mark, notes[mark])
