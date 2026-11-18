import statistics
from itertools import pairwise

from pdf2epub.labels import label_level, numeral_value
from pdf2epub.pdf import Line

from .layout import GAP, SPEECH_DASHES, Layout, has_gap_before, is_indented, is_tall

MIN_LINES = 4
MIN_INTRODUCED_LINES = 2
MAX_DIALOGUE_SHARE = 1 / 3
SHORT = 4
MIN_NARRATION_WORDS = 3
MAX_SENTENCE_SHARE = 0.5
CLOSING = (".", ",", "!", "?", ";", ")", "»")
SENTENCE_END = (".", "!", "?", "…")
CLOSING_QUOTES = '“”"»’'


def find_verse(lines: list[Line], layout: Layout) -> dict[int, bool]:
    verse: dict[int, bool] = {}
    run: list[int] = []
    for index in range(len(lines) + 1):
        if index < len(lines) and is_verse_line(lines[index], layout):
            run.append(index)
            continue
        run = without_paragraph_end(run, lines, layout)
        while run and (is_dialogue(lines[run[-1]]) or lines[run[-1]].text.endswith(":")):
            run = run[:-1]
        if (
            len(run) > 1
            and all(ends_sentence(lines[index].text) for index in run[-2:])
            and len(lines[run[-1]].text.split()) >= MIN_NARRATION_WORDS
            and is_verse(run[:-1], lines, layout)
        ):
            run = run[:-1]
        for part in [run] if is_verse(run, lines, layout) else between_dialogue(run, lines, layout):
            if is_verse(part, lines, layout):
                verse.update(stanzas(part, lines, layout))
        run = []
    return verse


def is_verse_line(line: Line, layout: Layout) -> bool:
    return (
        line.x1 < layout.right - SHORT * layout.line_height
        and not line.text.startswith(CLOSING)
        and not is_tall(line, layout)
        and label_level(line.text) is None
        and numeral_value(line.text) is None
    )


def without_paragraph_end(run: list[int], lines: list[Line], layout: Layout) -> list[int]:
    while run and (
        is_dialogue(lines[run[0]])
        or continues(run[0], lines, layout)
        or ends_sentence(lines[run[0]].text)
        or lines[run[0]].text.endswith(":")
    ):
        run = run[1:]
    return run


def continues(index: int, lines: list[Line], layout: Layout) -> bool:
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


def is_verse(run: list[int], lines: list[Line], layout: Layout) -> bool:
    if not run:
        return False
    sung = [index for index in run if not is_dialogue(lines[index])]
    ends = sum(1 for index in sung if ends_sentence(lines[index].text))
    dialogue = len(run) - len(sung)
    introduced = run[0] > 0 and is_introduction(lines[run[0] - 1], layout)
    return (
        len(run) >= (MIN_INTRODUCED_LINES if introduced else MIN_LINES)
        and ends <= MAX_SENTENCE_SHARE * len(sung)
        and dialogue <= MAX_DIALOGUE_SHARE * len(run)
    )


def is_introduction(line: Line, layout: Layout) -> bool:
    text = line.text
    return text.endswith(":") or (text.endswith(",") and is_verse_line(line, layout))


def is_dialogue(line: Line) -> bool:
    return line.text.startswith(SPEECH_DASHES)


def ends_sentence(text: str) -> bool:
    return text.rstrip(CLOSING_QUOTES).endswith(SENTENCE_END)


def stanzas(run: list[int], lines: list[Line], layout: Layout) -> dict[int, bool]:
    gaps = [lines[below].y0 - lines[above].y1 for above, below in pairwise(run)]
    usual = statistics.median(gaps)
    starts = {run[0]: True}
    for (_, below), gap in zip(pairwise(run), gaps, strict=True):
        starts[below] = gap > usual + GAP * layout.line_height
    return starts
