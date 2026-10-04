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
            start, end = block
            found = {
                mark: Note(f"note-{len(notes) + number}", mark, text)
                for number, (mark, text) in enumerate(
                    split_notes(section.paragraphs[start + 1 : end]), start=1
                )
            }
            notes.extend(found.values())
            del section.paragraphs[start:end]
            for marked in waiting:
                link_marks(marked, found)
            waiting = [section]
    return notes


def find_block(paragraphs: list[Paragraph]) -> tuple[int, int] | None:
    """Where a notes title and the notes under it are: [start, end).

    A long note may go on in a paragraph of its own, so the notes reach the last
    paragraph that starts one.
    """
    for index, paragraph in enumerate(paragraphs[:-1]):
        if paragraph.text.strip().casefold() in TITLES and NOTE_START.match(
            paragraphs[index + 1].text
        ):
            starts = [
                number
                for number in range(index + 1, len(paragraphs))
                if NOTE_START.match(paragraphs[number].text)
            ]
            return index, starts[-1] + 1
    return None


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
