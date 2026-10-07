import statistics
from itertools import pairwise

from bookflow.labels import label_level, numeral_value
from bookflow.pdf import Line

from .layout import GAP, Layout, has_gap_before, is_indented, is_tall

# Verse, a list, a column of names: this many short lines in a row at least...
MIN_LINES = 4

# ...or this many, after a line leading into them: "…და სიმღერა დაიწყო:".
MIN_INTRODUCED_LINES = 2

# A song may have speech in it, "- ტილო გარეცხე!", but at most this share of its lines.
MAX_DIALOGUE_SHARE = 1 / 3

# A line ending this many line heights short of the right edge is short even in
# ragged-right text.
SHORT = 4

# Short lines that each end a sentence are short paragraphs of text, not verse.
MAX_SENTENCE_SHARE = 0.5

DIALOGUE = ("-", "–", "—")

# A line opening with these ends the text above it: "!(არ გააჭირე საქმე...)".
CLOSING = (".", ",", "!", "?", ";", ")", "»")
SENTENCE_END = (".", "!", "?", "…")
CLOSING_QUOTES = '“”"»’'


def find_verse(lines: list[Line], layout: Layout) -> dict[int, bool]:
    """The page's lines that are verse (or a list), each mapped to whether it starts a stanza.

    Verse keeps its line breaks; a wider gap than its own lines' parts stanzas.
    """
    verse: dict[int, bool] = {}
    run: list[int] = []
    for index in range(len(lines) + 1):
        if index < len(lines) and is_verse_line(lines[index], layout):
            run.append(index)
            continue
        run = without_paragraph_end(run, lines, layout)
        # Nor does it end with speech or a line leading into it: "- საწყალი ცხენი,
        # - ამოიოხრა ფანტინმა." / "დალიამ იუცხოვა ეს სიბრალული:".
        while run and (is_dialogue(lines[run[-1]]) or lines[run[-1]].text.endswith(":")):
            run = run[:-1]
        # Speech may break up a song; if the whole run isn't verse, its parts between
        # the speech may be.
        for part in [run] if is_verse(run, lines) else between_dialogue(run, lines, layout):
            if is_verse(part, lines):
                verse.update(stanzas(part, lines, layout))
        run = []
    return verse


def is_verse_line(line: Line, layout: Layout) -> bool:
    """A short line; one opening speech counts too, but no run of verse starts with it."""
    return (
        line.x1 < layout.right - SHORT * layout.line_height
        and not line.text.startswith(CLOSING)
        and not is_tall(line, layout)
        and label_level(line.text) is None
        and numeral_value(line.text) is None
    )


def without_paragraph_end(run: list[int], lines: list[Line], layout: Layout) -> list[int]:
    """Leave out the text before the verse: the last line of the paragraph above, or
    a short paragraph leading into it ("…იმღერა ჰანგი:", "და ისევ მოკურცხლა.").
    """
    while run and (
        is_dialogue(lines[run[0]])
        or continues(run[0], lines, layout)
        or ends_sentence(lines[run[0]].text)
        or lines[run[0]].text.endswith(":")
    ):
        run = run[1:]
    return run


def continues(index: int, lines: list[Line], layout: Layout) -> bool:
    """Carries on the line above it: no indent, no gap, and the line above isn't verse."""
    if index == 0:
        return False
    line, above = lines[index], lines[index - 1]
    return not (
        is_indented(line, layout)
        or has_gap_before(line, above, layout)
        or is_verse_line(above, layout)
    )


def between_dialogue(run: list[int], lines: list[Line], layout: Layout) -> list[list[int]]:
    parts: list[list[int]] = [[]]
    for index in run:
        if is_dialogue(lines[index]):
            parts.append([])
        else:
            parts[-1].append(index)
    return [without_paragraph_end(part, lines, layout) for part in parts]


def is_verse(run: list[int], lines: list[Line]) -> bool:
    if not run:
        return False
    # Speech in a song ends its sentences as speech does; count the song's own lines.
    sung = [index for index in run if not is_dialogue(lines[index])]
    ends = sum(1 for index in sung if ends_sentence(lines[index].text))
    dialogue = len(run) - len(sung)
    introduced = run[0] > 0 and lines[run[0] - 1].text.endswith(":")
    return (
        len(run) >= (MIN_INTRODUCED_LINES if introduced else MIN_LINES)
        and ends <= MAX_SENTENCE_SHARE * len(sung)
        and dialogue <= MAX_DIALOGUE_SHARE * len(run)
    )


def is_dialogue(line: Line) -> bool:
    return line.text.startswith(DIALOGUE)


def ends_sentence(text: str) -> bool:
    return text.rstrip(CLOSING_QUOTES).endswith(SENTENCE_END)


def stanzas(run: list[int], lines: list[Line], layout: Layout) -> dict[int, bool]:
    """Some books space verse wider than text, so a stanza break is wide for the verse."""
    gaps = [lines[below].y0 - lines[above].y1 for above, below in pairwise(run)]
    usual = statistics.median(gaps)
    starts = {run[0]: True}
    for (_, below), gap in zip(pairwise(run), gaps, strict=True):
        starts[below] = gap > usual + GAP * layout.line_height
    return starts
