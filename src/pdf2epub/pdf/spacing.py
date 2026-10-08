"""Spaces for PDFs that set words apart by position alone, with no space characters.

Some PDFs place each word where it belongs but leave out the spaces between them,
and their fonts' widths are wrong, so the letters' boxes overlap and show no gap
either. Where each letter starts is still right, though: inside a word a letter
always moves the next one along by the same amount, and a word break moves it by
a space more.
"""

from collections import Counter, defaultdict
from collections.abc import Iterable
from itertools import pairwise
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

# Punctuation that ends a word: a letter right after it starts the next one.
WORD_END = ",.;:!?)]»”…"


class Glyph(NamedTuple):
    char: str
    x: float  # where the letter starts
    size: float
    font: str


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


def spaced_text(glyphs: list[Glyph], advances: Advances) -> str:
    """The line's text with a space at every word break."""
    text = []
    for index, glyph in enumerate(glyphs):
        if index and is_word_break(glyphs[index - 1], glyph, advances):
            text.append(" ")
        text.append(glyph.char)
    return "".join(text)


def is_word_break(glyph: Glyph, following: Glyph, advances: Advances) -> bool:
    if " " in (glyph.char, following.char):
        return False
    if glyph.char in WORD_END and following.char.isalpha():
        return True
    usual = advances.get((glyph.font, glyph.char))
    return usual is not None and advance(glyph, following) - usual > WORD_GAP


def advance(glyph: Glyph, following: Glyph) -> float:
    return (following.x - glyph.x) / glyph.size
