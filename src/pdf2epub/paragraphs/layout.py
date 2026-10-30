import statistics
from dataclasses import dataclass, replace
from itertools import pairwise

from pdf2epub.pdf import Line, Page

# A paragraph's first line is indented by about a line height; scans drift by less.
INDENT = 0.8

# A gap this many line heights wider than usual separates paragraphs (or headings).
GAP = 0.8

# A line ending this many line heights short of the right edge doesn't fill the line.
SHORT = 2

# A line this many times the usual height is set in a bigger font: a heading.
TALL = 1.3

# A line starting this many line heights right of the next one is set apart from
# the text (centred or set right), not a paragraph's indented first line.
SET_APART = 4

# A page this many lines long or more, none at the book's margin, has a margin of
# its own if this share of its lines run to the right margin, as text does.
MIN_OWN_MARGIN = 10
MIN_FULL = 0.3

# The widest gap between lines, in line heights, taken as usual on a page: a title page's
# few spread-out lines have wide gaps that aren't. A book set wider throughout, such as
# double-spaced, has its own width instead.
USUAL_GAP = 0.5

# Text that stops above this share of the page height ends the page early.
FULL_PAGE = 0.75

# Text that stops this many lines above the book's usual bottom leaves a blank line
# there; one line short is only a paragraph kept from breaking across the page.
BLANK_LINE = 1.5

# Pages with fewer lines, like chapter openings, are too sparse to learn the book's layout from.
MIN_MEASURED_LINES = 10

SENTENCE_END = (".", "!", "?", "…", ":", "»", "“", '"')

# A title is a line or a few, never a paragraph of text.
TITLE_LINES = 3

# A title stands apart from the text by this many times the step from line to
# line (or from paragraph to paragraph, in a book that spaces them).
TITLE_SPACE = 1.8

# The dashes that open speech: "– მოვიდნენ!".
SPEECH_DASHES = ("-", "–", "—")

# How speech and quotes open a line: "– მოვიდნენ!", "„მაგრამ…".
OPENINGS = (*SPEECH_DASHES, "„", "«", '"', "[")

# A book indents its paragraphs when at least this share of its lines start indented.
MIN_INDENTED = 0.03

# Justified lines stop within this many line heights of the margin; most lines do,
# and few stop between that and a short line's distance.
JUSTIFIED_SLACK = 0.5
MIN_FLUSH = 0.6
MAX_BETWEEN = 0.05

# A line this share of the column wide is text running on, not a heading.
LONG_LINE = 0.6

# Some books mark paragraphs by extra space instead of an indent: a line step this
# many times the usual one...
WIDE_STEP = (1.2, 2.5)

# ...on at least this share of lines, nearly all after a sentence's end. Word exports
# with hard breaks have the space mid-sentence too.
MIN_SPACED = 0.02
SPACED_AFTER_SENTENCE = 0.9


@dataclass
class Layout:
    """The usual geometry of a page's text, to tell when a line breaks from it."""

    left: float
    right: float
    line_height: float
    gap: float
    height: float
    # The step from one line to the next that marks a new paragraph, in a book that
    # sets paragraphs apart by space; None in a book that doesn't.
    paragraph_step: float | None = None
    # The book opens its paragraphs with an indent.
    indents: bool = False
    # The book has space between lines mid-sentence too, so space alone ends nothing.
    loose: bool = False
    # The widest gap between lines taken as usual, in line heights (USUAL_GAP).
    usual_gap: float = USUAL_GAP
    # The book's lines run to the right margin, all but a paragraph's last.
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
    """The page's usual gap between lines, in line heights."""
    line_height = statistics.median(line.height for line in page.lines)
    gaps = [below.y0 - above.y1 for above, below in pairwise(page.lines)]
    return max(statistics.median(gaps), 0) / line_height if gaps and line_height else 0


def text_column(pages: list[Page]) -> Layout:
    """The book's usual text column."""
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
    """Whether the book's lines run to the right margin: they stop within a hair of it
    or well short, never in between as ragged text does."""
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
    """Whether the book indents its paragraphs: enough lines start at an indent."""
    lines = indented = 0
    for page in measured(pages):
        layout = measure(page)
        lines += len(page.lines)
        indented += sum(
            INDENT < (line.x0 - layout.left) / layout.line_height < SET_APART for line in page.lines
        )
    return indented >= MIN_INDENTED * lines if lines else False


def spacing(pages: list[Page]) -> tuple[float | None, bool]:
    """The line step that starts a paragraph, if the book marks paragraphs by space, and
    whether it has such space mid-sentence too, as Word exports with hard breaks do."""
    found = wide_steps(pages)
    if found is None:
        return None, False
    usual, wide, marks_paragraphs = found
    if not marks_paragraphs:
        return None, True
    return (usual + statistics.median(step for step, _ in wide)) / 2, False


def wide_steps(pages: list[Page]) -> tuple[float, list[tuple[float, Line]], bool] | None:
    """The usual line step, the wider ones, and whether those mark paragraphs; None
    when wide steps are too rare to tell."""
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
    """A page's own margins, unless they are far off the book's, as on a page of
    dialogue. A page set narrower on the left, like notes at the back, keeps its own."""
    full = [line for line in page.lines if column.right - line.x1 <= SHORT * column.line_height]
    own_margin = (
        len(page.lines) >= MIN_OWN_MARGIN
        and len(full) >= MIN_FULL * len(page.lines)
        and all(line.x0 - column.left > INDENT * column.line_height for line in page.lines)
    )
    if own_margin:
        # Its full lines show the margins: short notes leave most lines short.
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
    """Ends a sentence, a bracket or a note mark: "...იწვა.", "...miux.[10]"."""
    return text.endswith((*SENTENCE_END, ")", "]"))


def is_indented(line: Line, layout: Layout) -> bool:
    return line.x0 - layout.left > INDENT * layout.line_height


def has_gap_before(line: Line, previous: Line, layout: Layout) -> bool:
    """Set below the line above by more than the usual gap. In a loosely spaced book a
    long line running on mid-sentence carries on across it, unless speech opens."""
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
    """Set below the line above by a paragraph's space, in a book that marks them so,
    after a sentence's end or before speech."""
    step = layout.paragraph_step
    if step is None or line.y0 - above.y0 < step:
        return False
    return ends_sentence(above.text) or line.text.startswith(OPENINGS)


def stands_apart(line: Line, above: Line, layout: Layout) -> bool:
    """Far below the line above, as a heading is: more than a paragraph's space."""
    usual = layout.paragraph_step or layout.line_height + layout.gap
    return line.y0 - above.y0 > TITLE_SPACE * usual


def is_tall(line: Line, layout: Layout) -> bool:
    """Set in a bigger font than the text, as headings often are."""
    return line.height > TALL * layout.line_height


def is_set_apart(line: Line, following: Line, layout: Layout) -> bool:
    """Starts far right of the line after it, as a centred or right-aligned heading does."""
    return line.x0 - following.x0 > SET_APART * layout.line_height


def ends_page_early(line: Line, layout: Layout) -> bool:
    """The page's text stops well above the bottom: a title page or a chapter's end."""
    return line.y1 < FULL_PAGE * layout.height


def text_bottom(pages: list[Page]) -> float:
    """Where the book's pages usually stop: the bottom of a full page's last line."""
    return statistics.median(page.lines[-1].y1 for page in pages if page.lines)


def text_top(pages: list[Page]) -> float:
    """Where the book's pages usually start: the top of a page's first line."""
    return statistics.median(page.lines[0].y0 for page in pages if page.lines)


def starts_with_blank_line(line: Line, layout: Layout, top: float) -> bool:
    """The page's first line starts a blank line or more below the top, as a chapter
    marked only by a blank line starts when it falls at a page's head."""
    step = layout.line_height + layout.gap
    return line.y0 - top > BLANK_LINE * step


def ends_with_blank_line(line: Line, layout: Layout, bottom: float) -> bool:
    """The page's last line ends a sentence a blank line or more above the bottom,
    as a chapter marked only by a blank line ends when it falls at a page's foot."""
    step = layout.line_height + layout.gap
    return bottom - line.y1 > BLANK_LINE * step and ends_sentence(line.text)


def is_short(line: Line, layout: Layout) -> bool:
    """Stops short of the right edge: not a full line of text."""
    return layout.right - line.x1 > SHORT * layout.line_height


def ends_paragraph(line: Line, layout: Layout) -> bool:
    """Stops short of the right edge after the end of a sentence.

    In justified text any line stopping short of the margin is a paragraph's last.
    """
    short = JUSTIFIED_SLACK if layout.justified else SHORT
    return layout.right - line.x1 > short * layout.line_height and line.text.endswith(SENTENCE_END)
