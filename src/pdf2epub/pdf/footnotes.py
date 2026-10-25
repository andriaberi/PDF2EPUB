import re

from .models import Footnote, Line, Page
from .text import RAISED_MARK

# A footnote opens with its number: "1 text", "79text", "[1] text".
NUMBERED = re.compile(r"^\[?(\d{1,3})\]?\s*")


def marked_footnotes(notes: list[Line], text: list[Line]) -> list[Footnote]:
    """The footnotes whose numbers are raised marks in the page's text, with their lines
    run together; a footnote whose mark can't be found is dropped."""
    found: list[Footnote] = []
    for line in notes:
        if (opening := NUMBERED.match(line.text)) is not None:
            found.append(Footnote(opening.group(1), line.text[opening.end() :]))
        elif found:
            found[-1].text = f"{found[-1].text} {line.text}"
    marks = {mark for line in text for mark in RAISED_MARK.findall(line.text)}
    return [note for note in found if note.mark in marks]


def number_footnotes(pages: list[Page]) -> None:
    """Number the footnotes through the book and make their raised marks note marks,
    "[12]": a book that numbers them from 1 on every page still links each to its own.
    A raised mark with no footnote found is taken out."""
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
