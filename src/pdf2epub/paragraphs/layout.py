import statistics
from dataclasses import dataclass, replace
from itertools import pairwise

from pdf2epub.pdf import Line, Page

INDENT = 0.8
GAP = 0.8
SHORT = 2
TALL = 1.3
SET_APART = 4
MIN_OWN_MARGIN = 10
MIN_FULL = 0.3
USUAL_GAP = 0.5
FULL_PAGE = 0.75
BLANK_LINE = 1.5
MIN_MEASURED_LINES = 10
SENTENCE_END = (".", "!", "?", "…", ":", "»", "“", '"')
TITLE_LINES = 3
TITLE_SPACE = 1.8
SPEECH_DASHES = ("-", "–", "—")
OPENINGS = (*SPEECH_DASHES, "„", "«", '"', "[")
MIN_INDENTED = 0.03
JUSTIFIED_SLACK = 0.5
MIN_FLUSH = 0.6
MAX_BETWEEN = 0.05
LONG_LINE = 0.6

# A line step this many usual steps wide marks a paragraph in books spaced, not indented.
WIDE_STEP = (1.2, 2.5)
MIN_SPACED = 0.02
SPACED_AFTER_SENTENCE = 0.9


@dataclass
class Layout:
    left: float
    right: float
    line_height: float
    gap: float
    height: float
    # None when the book doesn't space its paragraphs.
    paragraph_step: float | None = None
    indents: bool = False
    # Space mid-sentence too, so space alone ends nothing.
    loose: bool = False
    usual_gap: float = USUAL_GAP
    justified: bool = False


def measure(page: Page, usual_gap: float = USUAL_GAP) -> Layout:
    lines = page.lines
    line_height = statistics.median(line.height for line in lines)
    gap = min(spread(page), usual_gap) * line_height
    return Layout(
        left=statistics.median(line.x0 for line in lines),
        right=statistics.median(line.x1 for line in lines),
        line_height=line_height,
        gap=gap,
        height=page.height,
        usual_gap=usual_gap,
    )


def spread(page: Page) -> float:
    line_height = statistics.median(line.height for line in page.lines)
    gaps = [below.y0 - above.y1 for above, below in pairwise(page.lines)]
    return max(statistics.median(gaps), 0) / line_height if gaps and line_height else 0


def text_column(pages: list[Page]) -> Layout:
    full = measured(pages)
    usual_gap = (
        max(USUAL_GAP, statistics.median(spread(page) for page in full)) if full else USUAL_GAP
    )
    layouts = [measure(page, usual_gap) for page in full] or [
        measure(page) for page in pages if page.lines
    ]
    step, loose = spacing(pages)
    return Layout(
        left=statistics.median(layout.left for layout in layouts),
        right=statistics.median(layout.right for layout in layouts),
        line_height=statistics.median(layout.line_height for layout in layouts),
        gap=statistics.median(layout.gap for layout in layouts),
        height=statistics.median(layout.height for layout in layouts),
        paragraph_step=step,
        indents=indents(pages),
        loose=loose,
        justified=is_justified(pages),
        usual_gap=usual_gap,
    )


def measured(pages: list[Page]) -> list[Page]:
    return [page for page in pages if len(page.lines) >= MIN_MEASURED_LINES]


def is_justified(pages: list[Page]) -> bool:
    flush = between = lines = 0
    for page in measured(pages):
        layout = measure(page)
        for line in page.lines:
            slack = abs(layout.right - line.x1) / layout.line_height
            lines += 1
            flush += slack < JUSTIFIED_SLACK
            between += JUSTIFIED_SLACK <= slack < SHORT
    return lines > 0 and flush >= MIN_FLUSH * lines and between <= MAX_BETWEEN * lines


def indents(pages: list[Page]) -> bool:
    lines = indented = 0
    for page in measured(pages):
        layout = measure(page)
        lines += len(page.lines)
        indented += sum(
            INDENT < (line.x0 - layout.left) / layout.line_height < SET_APART for line in page.lines
        )
    return indented >= MIN_INDENTED * lines if lines else False


def spacing(pages: list[Page]) -> tuple[float | None, bool]:
    found = wide_steps(pages)
    if found is None:
        return None, False
    usual, wide, marks_paragraphs = found
    if not marks_paragraphs:
        return None, True
    return (usual + statistics.median(step for step, _ in wide)) / 2, False


def wide_steps(pages: list[Page]) -> tuple[float, list[tuple[float, Line]], bool] | None:
    steps: list[tuple[float, Line]] = []
    for page in measured(pages):
        for above, below in pairwise(page.lines):
            if abs(below.height - above.height) < 0.2 * above.height:
                steps.append((below.y0 - above.y0, above))
    if not steps:
        return None
    usual = statistics.median(step for step, _ in steps)
    wide = [
        (step, above) for step, above in steps if WIDE_STEP[0] * usual < step < WIDE_STEP[1] * usual
    ]
    if len(wide) < MIN_SPACED * len(steps):
        return None
    after_sentence = sum(ends_sentence(above.text) for _, above in wide)
    return usual, wide, after_sentence >= SPACED_AFTER_SENTENCE * len(wide)


def fit(layout: Layout, column: Layout, page: Page) -> Layout:
    full = [line for line in page.lines if column.right - line.x1 <= SHORT * column.line_height]
    own_margin = (
        len(page.lines) >= MIN_OWN_MARGIN
        and len(full) >= MIN_FULL * len(page.lines)
        and all(line.x0 - column.left > INDENT * column.line_height for line in page.lines)
    )
    if own_margin:
        layout = replace(layout, left=min(line.x0 for line in full), right=column.right)
    elif (
        layout.left - column.left > INDENT * column.line_height
        or column.right - layout.right > SHORT * column.line_height
    ):
        return replace(column, line_height=layout.line_height, gap=layout.gap, height=layout.height)
    return replace(
        layout,
        paragraph_step=column.paragraph_step,
        indents=column.indents,
        loose=column.loose,
        justified=column.justified,
    )


def ends_sentence(text: str) -> bool:
    return text.endswith((*SENTENCE_END, ")", "]"))


def is_indented(line: Line, layout: Layout) -> bool:
    return line.x0 - layout.left > INDENT * layout.line_height


def has_gap_before(line: Line, previous: Line, layout: Layout) -> bool:
    if line.y0 - previous.y1 <= layout.gap + GAP * layout.line_height:
        return False
    runs_on = (
        layout.loose
        and not ends_sentence(previous.text)
        and previous.x1 - previous.x0 > LONG_LINE * (layout.right - layout.left)
        and not line.text.startswith(OPENINGS)
    )
    return not runs_on


def is_spaced_apart(line: Line, above: Line, layout: Layout) -> bool:
    step = layout.paragraph_step
    if step is None or line.y0 - above.y0 < step:
        return False
    return ends_sentence(above.text) or line.text.startswith(OPENINGS)


def stands_apart(line: Line, above: Line, layout: Layout) -> bool:
    usual = layout.paragraph_step or layout.line_height + layout.gap
    return line.y0 - above.y0 > TITLE_SPACE * usual


def is_tall(line: Line, layout: Layout) -> bool:
    return line.height > TALL * layout.line_height


def is_set_apart(line: Line, following: Line, layout: Layout) -> bool:
    return line.x0 - following.x0 > SET_APART * layout.line_height


def ends_page_early(line: Line, layout: Layout) -> bool:
    return line.y1 < FULL_PAGE * layout.height


def text_bottom(pages: list[Page]) -> float:
    return statistics.median(page.lines[-1].y1 for page in pages if page.lines)


def text_top(pages: list[Page]) -> float:
    return statistics.median(page.lines[0].y0 for page in pages if page.lines)


def starts_with_blank_line(line: Line, layout: Layout, top: float) -> bool:
    step = layout.line_height + layout.gap
    return line.y0 - top > BLANK_LINE * step


def ends_with_blank_line(line: Line, layout: Layout, bottom: float) -> bool:
    step = layout.line_height + layout.gap
    return bottom - line.y1 > BLANK_LINE * step and ends_sentence(line.text)


def is_short(line: Line, layout: Layout) -> bool:
    return layout.right - line.x1 > SHORT * layout.line_height


def ends_paragraph(line: Line, layout: Layout) -> bool:
    short = JUSTIFIED_SLACK if layout.justified else SHORT
    return layout.right - line.x1 > short * layout.line_height and line.text.endswith(SENTENCE_END)
