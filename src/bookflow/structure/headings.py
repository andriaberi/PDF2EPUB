import re

from bookflow.paragraphs import Paragraph
from bookflow.paragraphs.layout import Layout
from bookflow.pdf import Line

# Division words, outermost first. Georgian: ტომი volume, ნაწილი part, წიგნი book,
# თავი chapter.
LABELS = {
    "ტომი": 1,
    "volume": 1,
    "ნაწილი": 2,
    "part": 2,
    "წიგნი": 3,
    "book": 3,
    "თავი": 4,
    "chapter": 4,
}

# "Chapter 12", "CHAPTER XII.", "თავი მეორე", "მესამე ნაწილი". The number is one
# word because OCR garbles Georgian ordinals too much to spell-check them
# ("მეეჭპვგჭსე"). Only a numeral may take a full stop, so a sentence like
# "თავი დახარა." isn't a label.
LABEL = re.compile(r"^(\w+)\s+(\w+|\d+\.|[IVXLCDM]+\.)$", re.IGNORECASE)

# A title is a line or a few, never a paragraph of text.
MAX_TITLE_LINES = 3


def label_level(text: str) -> int | None:
    """The division level of a label like "თავი მეორე", allowing one OCR misread letter."""
    found = find_label(text)
    return LABELS[found[1]] if found else None


def fix_label(text: str) -> str:
    """Spell the label word right: OCR's "თაჭი მეორე" becomes "თავი მეორე"."""
    found = find_label(text)
    if found is None:
        return text
    index, label = found
    words = text.split()
    word = words[index]
    if word.isupper():
        label = label.upper()
    elif word[0].isupper():
        label = label.capitalize()
    words[index] = label
    return " ".join(words)


def find_label(text: str) -> tuple[int, str] | None:
    """Which word of the line is the label word, and which label it is.

    The label usually comes first ("ნაწილი მესამე") but may follow its number
    ("მესამე ნაწილი"). Second place takes only an exact match: "მისი თავს" is text.
    """
    match = LABEL.match(text)
    if not match:
        return None
    first, second = (word.lower() for word in match.groups())
    for label in LABELS:
        if len(first) == len(label) and sum(a != b for a, b in zip(first, label, strict=True)) <= 1:
            return 0, label
    if second in LABELS:
        return 1, second
    return None


def is_short(line: Line, layout: Layout) -> bool:
    """Stops well before the right margin, as a heading set flush left does."""
    return line.x1 < layout.right - 2 * layout.line_height


def is_centred(line: Line, layout: Layout) -> bool:
    """Set apart from both margins, around the middle of the text column."""
    margin = layout.line_height
    middle = (layout.left + layout.right) / 2
    return (
        line.x0 > layout.left + margin
        and line.x1 < layout.right - margin
        and abs((line.x0 + line.x1) / 2 - middle) < 2 * layout.line_height
    )


def is_label(paragraph: Paragraph, layout: Layout) -> bool:
    """A label alone on a short line, centred or not: books set headings either way."""
    return (
        len(paragraph.lines) == 1
        and is_short(paragraph.lines[0], layout)
        and label_level(paragraph.text) is not None
    )


def is_title(paragraph: Paragraph, layout: Layout) -> bool:
    """A line or a few, each centred or short: never a run of full lines of text."""
    return len(paragraph.lines) <= MAX_TITLE_LINES and all(
        is_centred(line, layout) or is_short(line, layout) for line in paragraph.lines
    )


def gap_after(paragraph: Paragraph, following: Paragraph | None, layout: Layout) -> bool:
    """A heading is set off from the text after it; a short paragraph of text isn't."""
    if following is None or following.page != paragraph.page:
        return True
    space = following.lines[0].y0 - paragraph.lines[-1].y1
    return space > layout.gap + layout.line_height / 2
