import re

from .models import Footnote, Line, Page
from .text import RAISED_CLOSE, RAISED_MARK, RAISED_OPEN

# The signs that mark footnotes instead of numbers: "*", "**", "†".
SIGNS = "*†‡"

# A footnote opens with its number or sign: "1 text", "79text", "[1] text", "* text".
NUMBERED = re.compile(rf"^\[?(\d{{1,3}}|[{SIGNS}]{{1,3}})\]?\s*")

# A mark set in the text's own size, not raised, is glued to the word it follows, or to
# the punctuation after it: "pneumonia79", "pneumonia.79", "word*".
AFTER_WORD = r"(?:(?<=[^\W\d_])|(?<=[^\W\d_][.,;:!?»“”\"’)]))"


def marked_footnotes(notes: list[Line], text: list[Line]) -> list[Footnote]:
    """The footnotes whose marks are in the page's text, with their lines run together;
    a footnote whose mark can't be found is dropped. A mark set in the text's own size
    is made a raised one, as if it were set so."""
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
    """Make each mark, found in the text's own size, a raised one: the first after the
    mark before it, as footnotes come in the order of their marks."""
    at = (0, 0)  # the line, and the place in it, the next mark is looked for from
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
    """The mark glued to a word: digits with no more after them, or signs, all of them."""
    if mark.isdigit():
        return re.compile(rf"{AFTER_WORD}{mark}(?!\d)")
    return re.compile(rf"(?<=\S)(?<![{SIGNS}]){re.escape(mark)}(?![{SIGNS}])")


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
