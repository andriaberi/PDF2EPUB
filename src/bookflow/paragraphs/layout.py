import statistics
from dataclasses import dataclass
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

# Text that stops above this share of the page height ends the page early.
FULL_PAGE = 0.75

SENTENCE_END = (".", "!", "?", "…", ":", "»", "“", '"')


@dataclass
class Layout:
    """The usual geometry of a page's text, to tell when a line breaks from it."""

    left: float
    right: float
    line_height: float
    gap: float
    height: float


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


def is_indented(line: Line, layout: Layout) -> bool:
    return line.x0 - layout.left > INDENT * layout.line_height


def has_gap_before(line: Line, previous: Line, layout: Layout) -> bool:
    return line.y0 - previous.y1 > layout.gap + GAP * layout.line_height


def is_tall(line: Line, layout: Layout) -> bool:
    """Set in a bigger font than the text, as headings often are."""
    return line.height > TALL * layout.line_height


def ends_page_early(line: Line, layout: Layout) -> bool:
    """The page's text stops well above the bottom: a title page or a chapter's end."""
    return line.y1 < FULL_PAGE * layout.height


def ends_paragraph(line: Line, layout: Layout) -> bool:
    """Stops short of the right edge after the end of a sentence."""
    short = layout.right - line.x1 > SHORT * layout.line_height
    return short and line.text.endswith(SENTENCE_END)
