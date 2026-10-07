import statistics
from dataclasses import dataclass, replace
from itertools import pairwise

from bookflow.pdf import Line, Page

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

# Text that stops above this share of the page height ends the page early.
FULL_PAGE = 0.75

SENTENCE_END = (".", "!", "?", "…", ":", "»", "“", '"')

# A title is a line or a few, never a paragraph of text.
TITLE_LINES = 3

# A title stands apart from the text by this many times the step from line to
# line (or from paragraph to paragraph, in a book that spaces them).
TITLE_SPACE = 1.8

# How speech and quotes open a line: "– მოვიდნენ!", "„მაგრამ…".
OPENINGS = ("-", "–", "—", "„", "«", '"', "[")

# A book indents its paragraphs when at least this share of its lines start indented.
MIN_INDENTED = 0.03

# Justified lines stop within this many line heights of the margin; most lines do,
# and few stop between that and a short line's distance.
JUSTIFIED_SLACK = 0.5
MIN_FLUSH = 0.6
MAX_BETWEEN = 0.05

# A line this share of the column wide is text running on, not a heading.
LONG_LINE = 0.6

# Some books leave out the indent and mark paragraphs with a little extra space
# above them instead. A step from line to line this many times the usual one is
# such a space...
WIDE_STEP = (1.2, 2.5)

# ...and a book marks paragraphs that way when at least this share of its lines
# have one, and nearly all of those follow the end of a sentence (or a note mark).
# Word exports with a hard break in every few lines have the space mid-sentence too.
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
    # The book's lines run to the right margin, all but a paragraph's last.
    justified: bool = False


def measure(page: Page) -> Layout:
    lines = page.lines
    line_height = statistics.median(line.height for line in lines)
    gaps = [below.y0 - above.y1 for above, below in pairwise(lines)]
    # On a title page with a few spread-out lines every gap is wide; don't call that usual.
    gap = min(max(statistics.median(gaps), 0), line_height / 2) if gaps else 0
    return Layout(
        left=statistics.median(line.x0 for line in lines),
        right=statistics.median(line.x1 for line in lines),
        line_height=line_height,
        gap=gap,
        height=page.height,
    )


def text_column(pages: list[Page]) -> Layout:
    """The book's usual text column. Chapter openings are too sparse to measure alone."""
    layouts = [measure(page) for page in pages if len(page.lines) >= 10] or [
        measure(page) for page in pages if page.lines
    ]
    return Layout(
        left=statistics.median(layout.left for layout in layouts),
        right=statistics.median(layout.right for layout in layouts),
        line_height=statistics.median(layout.line_height for layout in layouts),
        gap=statistics.median(layout.gap for layout in layouts),
        height=statistics.median(layout.height for layout in layouts),
        paragraph_step=paragraph_step(pages),
        indents=indents(pages),
        loose=loose_spacing(pages),
        justified=is_justified(pages),
    )


def is_justified(pages: list[Page]) -> bool:
    """Whether the book's lines run to the right margin, so any shorter line ends.

    In justified text lines stop within a hair of the margin or well short of it;
    ragged text stops anywhere between.
    """
    flush = between = lines = 0
    for page in pages:
        if len(page.lines) < 10:
            continue
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
    for page in pages:
        if len(page.lines) < 10:
            continue
        layout = measure(page)
        lines += len(page.lines)
        indented += sum(
            INDENT < (line.x0 - layout.left) / layout.line_height < SET_APART for line in page.lines
        )
    return indented >= MIN_INDENTED * lines if lines else False


def paragraph_step(pages: list[Page]) -> float | None:
    """The line step that starts a paragraph, if the book marks paragraphs by space."""
    found = wide_steps(pages)
    if found is None or not found[2]:
        return None
    usual, wide, _ = found
    return (usual + statistics.median(step for step, _ in wide)) / 2


def loose_spacing(pages: list[Page]) -> bool:
    """Whether the book has space between lines that isn't a paragraph's.

    A Word export with a hard break every few lines puts the paragraph space after
    each of them, mid-sentence too: "...მთელი ორი-სამი" / "დღით მოსვენებას...".
    """
    found = wide_steps(pages)
    return found is not None and not found[2]


def wide_steps(pages: list[Page]) -> tuple[float, list[tuple[float, Line]], bool] | None:
    """The usual line step, the wider ones, and whether those mark paragraphs; None
    when wide steps are too rare to tell."""
    steps: list[tuple[float, Line]] = []
    for page in pages:
        if len(page.lines) < 10:
            continue
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
    after_sentence = sum(above.text.endswith((*SENTENCE_END, ")", "]")) for _, above in wide)
    return usual, wide, after_sentence >= SPACED_AFTER_SENTENCE * len(wide)


def fit(layout: Layout, column: Layout) -> Layout:
    """A page's own margins, unless they are far off the book's.

    A page of dialogue or verse has few full lines: its median line starts at the
    indent and stops short, so the page would take its indent for the margin.
    """
    if (
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


def is_indented(line: Line, layout: Layout) -> bool:
    return line.x0 - layout.left > INDENT * layout.line_height


def has_gap_before(line: Line, previous: Line, layout: Layout) -> bool:
    """Set below the line above by more than the usual gap.

    Where the book spaces lines loosely, a long line running on mid-sentence carries
    on its paragraph across the space, unless the next line opens speech.
    """
    if line.y0 - previous.y1 <= layout.gap + GAP * layout.line_height:
        return False
    runs_on = (
        layout.loose
        and not previous.text.endswith((*SENTENCE_END, ")", "]"))
        and previous.x1 - previous.x0 > LONG_LINE * (layout.right - layout.left)
        and not line.text.startswith(OPENINGS)
    )
    return not runs_on


def is_spaced_apart(line: Line, above: Line, layout: Layout) -> bool:
    """Set below the line above by a paragraph's space, in a book that marks them so.

    A sentence running on across the space carries on the paragraph, unless the
    line opens speech or a quote: the book left out a full stop.
    """
    step = layout.paragraph_step
    if step is None or line.y0 - above.y0 < step:
        return False
    return above.text.endswith((*SENTENCE_END, ")", "]")) or line.text.startswith(OPENINGS)


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


def is_short(line: Line, layout: Layout) -> bool:
    """Stops short of the right edge: not a full line of text."""
    return layout.right - line.x1 > SHORT * layout.line_height


def ends_paragraph(line: Line, layout: Layout) -> bool:
    """Stops short of the right edge after the end of a sentence.

    In justified text any line stopping short of the margin is a paragraph's last.
    """
    short = JUSTIFIED_SLACK if layout.justified else SHORT
    return layout.right - line.x1 > short * layout.line_height and line.text.endswith(SENTENCE_END)
