"""Spaces where the page shows them, whatever space characters the PDF has.

Some PDFs leave spaces out or have wrong font widths, but where each letter starts is
right: inside a word a letter moves the next by its usual amount, a word break by more.
"""

from collections import Counter, defaultdict
from collections.abc import Iterable
from itertools import pairwise
from statistics import median
from typing import NamedTuple

from .text import RAISED_CLOSE, RAISED_OPEN

# Text has about one space in seven characters; a book with fewer than this share
# has lost its spaces.
MIN_SPACE_SHARE = 0.05

# A letter moving the next this much further than usual, in font sizes, starts a
# word; a space is about a quarter of the font size.
WORD_GAP = 0.15

# A letter's usual advance is learned only from this many pairs at least.
MIN_SAMPLES = 20

# A line's letter-spacing is measured over this many pairs of letters at least: a
# word break in a fragment like "-C’" would pass for spacing.
MIN_TRACKED = 4

# Punctuation that ends a word: a letter right after it starts the next one.
WORD_END = ",.;:!?)]»”…"


class Glyph(NamedTuple):
    char: str
    x: float  # where the letter starts
    size: float
    font: str
    right: float | None = None  # where its box ends
    raised: bool = False  # a digit of a note mark set above the line: "pneumonia⁷⁹"


# A letter's usual advance in a font, in font sizes: (font, char) -> advance.
Advances = dict[tuple[str, str], float]


def lacks_spaces(texts: Iterable[str]) -> bool:
    chars = spaces = 0
    for text in texts:
        chars += len(text)
        spaces += text.count(" ")
    return chars > 0 and spaces < MIN_SPACE_SHARE * chars


def learn_advances(lines: Iterable[list[Glyph]]) -> Advances:
    """How far each letter usually moves the next: the most common distance, since most
    letters are followed by one of the same word."""
    distances: defaultdict[tuple[str, str], Counter[float]] = defaultdict(Counter)
    for glyphs in lines:
        for glyph, following in pairwise(glyphs):
            if " " not in (glyph.char, following.char) and glyph.font == following.font:
                distances[glyph.font, glyph.char][round(advance(glyph, following), 2)] += 1
    return {
        key: counts.most_common(1)[0][0]
        for key, counts in distances.items()
        if counts.total() >= MIN_SAMPLES
    }


def spaced_text(
    glyphs: list[Glyph], advances: Advances, tracking: float = 0.0, unspaced: bool = False
) -> str:
    """The line's text with a space at every word break and nowhere else. `tracking` is
    its letter-spacing; `unspaced`, a book without spaces, where punctuation ends words."""
    text: list[str] = []
    previous = None
    spaced = False  # a space character since the previous letter
    for glyph in glyphs:
        if glyph.char.isspace():
            spaced = True
            continue
        in_mark = previous is not None and previous.raised
        if in_mark and not glyph.raised:
            text.append(RAISED_CLOSE)
        # A raised note mark keeps to the word it follows: "pneumonia⁅79⁆".
        if glyph.raised and not in_mark:
            text.append(RAISED_OPEN)
        elif previous and is_word_break(previous, glyph, advances, tracking, spaced, unspaced):
            text.append(" ")
        text.append(glyph.char)
        previous, spaced = glyph, False
    if previous is not None and previous.raised:
        text.append(RAISED_CLOSE)
    return "".join(text)


def letter_spacing(glyphs: list[Glyph], advances: Advances) -> float | None:
    """How much further than usual the line moves each letter, as a s p a c e d name
    does; None when there are too few letters to tell."""
    extras = [
        advance(glyph, following) - usual
        for glyph, following in pairwise(glyphs)
        if not glyph.char.isspace()
        and not following.char.isspace()
        and (usual := advances.get((glyph.font, glyph.char))) is not None
    ]
    return max(median(extras), 0.0) if len(extras) >= MIN_TRACKED else None


def is_word_break(
    glyph: Glyph,
    following: Glyph,
    advances: Advances,
    tracking: float,
    spaced: bool,
    unspaced: bool,
) -> bool:
    if glyph.char in WORD_END and (spaced or (unspaced and following.char.isalpha())):
        return True
    usual = advances.get((glyph.font, glyph.char))
    if usual is None:
        # A font too rare to learn from: its spaces, or a gap between the letters'
        # boxes where it has none (boxes may overlap where widths are wrong).
        if spaced or glyph.right is None:
            return spaced
        return (following.x - glyph.right) / glyph.size - tracking > WORD_GAP
    return advance(glyph, following) - usual - tracking > WORD_GAP


def advance(glyph: Glyph, following: Glyph) -> float:
    return (following.x - glyph.x) / glyph.size
