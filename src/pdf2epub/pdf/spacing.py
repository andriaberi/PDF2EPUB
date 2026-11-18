from collections import Counter, defaultdict
from collections.abc import Iterable
from itertools import pairwise
from statistics import median
from typing import NamedTuple

from .text import RAISED_CLOSE, RAISED_OPEN

MIN_SPACE_SHARE = 0.05
WORD_GAP = 0.15
MIN_SAMPLES = 20
MIN_TRACKED = 4
WORD_END = ",.;:!?)]»”…"


class Glyph(NamedTuple):
    char: str
    x: float
    size: float
    font: str
    right: float | None = None
    raised: bool = False
    style: str = ""


Advances = dict[tuple[str, str], float]


def lacks_spaces(texts: Iterable[str]) -> bool:
    chars = spaces = 0
    for text in texts:
        chars += len(text)
        spaces += text.count(" ")
    return chars > 0 and spaces < MIN_SPACE_SHARE * chars


def learn_advances(lines: Iterable[list[Glyph]]) -> Advances:
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
    return "".join(char for char, _ in spaced_chars(glyphs, advances, tracking, unspaced))


def spaced_chars(
    glyphs: list[Glyph], advances: Advances, tracking: float = 0.0, unspaced: bool = False
) -> list[tuple[str, str]]:
    text: list[tuple[str, str]] = []
    previous = None
    spaced = False
    for glyph in glyphs:
        if glyph.char.isspace():
            spaced = True
            continue
        in_mark = previous is not None and previous.raised
        if in_mark and not glyph.raised:
            text.append((RAISED_CLOSE, ""))
        if glyph.raised and not in_mark:
            text.append((RAISED_OPEN, ""))
        elif previous and is_word_break(previous, glyph, advances, tracking, spaced, unspaced):
            text.append((" ", previous.style))
        text.append((glyph.char, glyph.style))
        previous, spaced = glyph, False
    if previous is not None and previous.raised:
        text.append((RAISED_CLOSE, ""))
    return text


def letter_spacing(glyphs: list[Glyph], advances: Advances) -> float | None:
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
        if spaced or glyph.right is None:
            return spaced
        return (following.x - glyph.right) / glyph.size - tracking > WORD_GAP
    return advance(glyph, following) - usual - tracking > WORD_GAP


def advance(glyph: Glyph, following: Glyph) -> float:
    return (following.x - glyph.x) / glyph.size
