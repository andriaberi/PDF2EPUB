import re

from .models import Footnote, Line, Page
from .text import RAISED_CLOSE, RAISED_MARK, RAISED_OPEN

SIGNS = "*†‡"

# "1 text", "79text", "[1] text", "* text"
NUMBERED = re.compile(rf"^\[?(\d{{1,3}}|[{SIGNS}]{{1,3}})\]?\s*")

# "pneumonia79", "pneumonia.79", "word*"
AFTER_WORD = r"(?:(?<=[^\W\d_])|(?<=[^\W\d_][.,;:!?»“”\"’)]))"


def marked_footnotes(notes: list[Line], text: list[Line]) -> list[Footnote]:
    found: list[Footnote] = []
    for line in notes:
        if (opening := NUMBERED.match(line.text)) is not None:
            found.append(Footnote(opening.group(1), line.text[opening.end() :]))
        elif found:
            found[-1].text = f"{found[-1].text} {line.text}"
    marks = {mark for line in text for mark in RAISED_MARK.findall(line.text)}
    raise_plain_marks([note.mark for note in found if note.mark not in marks], text)
    marks = {mark for line in text for mark in RAISED_MARK.findall(line.text)}
    return [note for note in found if note.mark in marks]


def raise_plain_marks(marks: list[str], text: list[Line]) -> None:
    at = (0, 0)
    for mark in marks:
        pattern = plain_mark(mark)
        for index in range(at[0], len(text)):
            line = text[index]
            start = at[1] if index == at[0] else 0
            if (found := pattern.search(line.text, start)) is not None:
                raised = f"{RAISED_OPEN}{mark}{RAISED_CLOSE}"
                line.text = line.text[: found.start()] + raised + line.text[found.end() :]
                at = (index, found.start() + len(raised))
                break


def plain_mark(mark: str) -> re.Pattern[str]:
    if mark.isdigit():
        return re.compile(rf"{AFTER_WORD}{mark}(?!\d)")
    return re.compile(rf"(?<=\S)(?<![{SIGNS}]){re.escape(mark)}(?![{SIGNS}])")


def number_footnotes(pages: list[Page]) -> None:
    count = 0
    for page in pages:
        numbers: dict[str, str] = {}
        for note in page.footnotes:
            count += 1
            numbers.setdefault(note.mark, str(count))
            note.mark = str(count)
        for line in page.lines:
            line.text = note_marks(line.text, numbers)


def note_marks(text: str, numbers: dict[str, str]) -> str:
    def mark(raised: re.Match[str]) -> str:
        number = numbers.get(raised.group(1))
        return f"[{number}]" if number else ""

    return RAISED_MARK.sub(mark, text)
