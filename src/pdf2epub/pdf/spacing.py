"""Spaces where the page shows them, whatever space characters the PDF has.

Some PDFs place each word where it belongs but leave out the spaces between them,
some leave out only a few, and some put a space of no width wherever a word may be
split across lines. Their fonts' widths may be wrong too, so the letters' boxes
overlap and show no gap. Where each letter starts is still right, though: inside a
word a letter always moves the next one along by the same amount, and a word break
moves it by a space more.
"""

from collections import Counter, defaultdict
from collections.abc import Iterable
from itertools import pairwise
from statistics import median
from typing import NamedTuple

# Text has about one space in seven characters; a book with fewer than this share
# has lost its spaces.
MIN_SPACE_SHARE = 0.05

# A letter moving the next one this much further than usual, in font sizes, starts
# a new word. A space is about a quarter of the font size; letters inside a word
# move the next by exactly their usual amount.
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


# A letter's usual advance in a font, in font sizes: (font, char) -> advance.
Advances = dict[tuple[str, str], float]


def lacks_spaces(texts: Iterable[str]) -> bool:
    chars = spaces = 0
    for text in texts:
        chars += len(text)
        spaces += text.count(" ")
    return chars > 0 and spaces < MIN_SPACE_SHARE * chars


def learn_advances(lines: Iterable[list[Glyph]]) -> Advances:
    """How far each letter usually moves the next one: the most common distance.

    Most letters are followed by another letter of the same word, so the most common
    distance is the letter's own width.
    """
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
    """The line's text with a space at every word break and nowhere else.

    `tracking` is the line's letter-spacing. `unspaced` is for a book without space
    characters, where punctuation always ends a word: its learned advance takes the
    missing space in.
    """
    text: list[str] = []
    previous = None
    spaced = False  # a space character since the previous letter
    for glyph in glyphs:
        if glyph.char.isspace():
            spaced = True
            continue
        if previous and is_word_break(previous, glyph, advances, tracking, spaced, unspaced):
            text.append(" ")
        text.append(glyph.char)
        previous, spaced = glyph, False
    return "".join(text)


def letter_spacing(glyphs: list[Glyph], advances: Advances) -> float | None:
    """How much further than usual the text moves each letter: a s p a c e d  o u t
    name, set without spaces, moves every letter along by more than a word break would.

    None when there are too few letters to tell.
    """
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
