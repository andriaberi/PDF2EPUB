import re
import statistics
from collections import Counter
from itertools import pairwise

from .models import Line, Page
from .text import script_of, strip_edge_debris

# How far into the top or bottom of the page headers, footers and page numbers sit.
MARGIN = 0.12

# Furniture is peeled off the edges; a page rarely has more than this on one side.
MAX_EDGE_LINES = 3

# A running header or footer has to repeat on at least this many pages.
MIN_REPEATS = 3

PUNCTUATION = re.compile(r"^\W+|\W+$")
ROMAN = re.compile(r"^[ivxlcdm]+\.?$", re.IGNORECASE)
NUMBER = re.compile(r"^[\d.,:;/()\[\]–—-]+$")
SEPARATOR = re.compile(r"^[*⁂•·~=_—–\- ]+$")

# Footnotes sit in the bottom part of the page, below a gap wider than this many
# ordinary line gaps (or half a line), and take up at most this many lines.
FOOTNOTE_AREA = 0.6
FOOTNOTE_GAP = 3
MAX_FOOTNOTE_LINES = 6

# The footnote's reference mark. OCR reads a small raised "¹" as all sorts of
# things ("'!", "%", "31"), so accept short runs of digits and symbols. Dashes
# are left out: they start dialogue lines.
FOOTNOTE_MARK = re.compile(r"^[\d*†‡§'’\"“”!%^°¹²³⁰⁴-⁹]{1,3}[.)]?$")


def remove_noise(pages: list[Page]) -> list[Page]:
    """Drop OCR junk, page numbers and running headers and footers."""
    for page in pages:
        page.lines = drop_junk(page.lines)
        # A page without a single real word is a cover or a plate read as text.
        if not any(has_long_word(line.text) for line in page.lines):
            page.lines = []

    repeated = repeated_edge_lines(pages)
    removed = {page.number: strip_edges(page, repeated) for page in pages}

    offset = page_number_offset(removed)
    if offset is not None:
        for page in pages:
            strip_glued_page_number(page, page.number + offset)

    for page in pages:
        # Footnote marks look like specks, so clean the edges only once footnotes are out.
        split_footnotes(page)
        for line in page.lines:
            line.text = strip_edge_debris(line.text)
        page.lines = [line for line in page.lines if line.text]

    return pages


def drop_junk(lines: list[Line]) -> list[Line]:
    """Remove lines that are OCR misreads of pictures, stains or decorations.

    When most of a page is junk (a cover or a plate), the stray letters and short
    words left between the junk go too; only lines with a real word stay.
    """
    kept = [line for line in lines if not is_junk(line.text)]
    junk = len(lines) - len(kept)
    if junk >= 2 and junk >= len(kept):
        kept = [line for line in kept if has_long_word(line.text)]
    return kept


def is_junk(text: str) -> bool:
    if SEPARATOR.match(text) or NUMBER.match(text) or ROMAN.match(text):
        return False

    good = bad = 0
    for token in text.split():
        word = PUNCTUATION.sub("", token)
        if not any(c.isalpha() for c in word):
            continue
        if is_word(word):
            good += len(word) > 1
        else:
            bad += 1

    return good == 0 or bad >= good


def has_long_word(text: str) -> bool:
    for token in text.split():
        word = PUNCTUATION.sub("", token)
        if sum(c.isalpha() for c in word) >= 4 and is_word(word):
            return True
    return False


def is_word(token: str) -> bool:
    """Letters of one script, with only apostrophes, hyphens or dots inside."""
    scripts = {script_of(c) for c in token if c.isalpha()}
    if len(scripts) != 1:
        return False
    return all(c.isalpha() or c in "'’-." for c in token)


def is_furniture(line: Line, page: Page, repeated: set[str]) -> bool:
    in_margin = line.y1 < page.height * MARGIN or line.y0 > page.height * (1 - MARGIN)
    if not in_margin:
        return False
    return is_page_number(line.text) or furniture_key(line.text) in repeated


def is_page_number(text: str) -> bool:
    """Short, with no real word: "12", "- 12 -", "xiv", or OCR misreads like "1,"."""
    compact = text.replace(" ", "")
    if len(compact) > 8:
        return False
    if ROMAN.match(compact):
        return True
    return not re.search(r"[^\W\d_]{2,}", text)


def furniture_key(text: str) -> str:
    """Headers repeat with a different page number each time, so ignore the digits."""
    return re.sub(r"[\d\W_]+", " ", text).strip().lower()


def edge_lines(page: Page) -> list[Line]:
    lines = page.lines
    if len(lines) <= 2 * MAX_EDGE_LINES:
        return lines
    return lines[:MAX_EDGE_LINES] + lines[-MAX_EDGE_LINES:]


def repeated_edge_lines(pages: list[Page]) -> set[str]:
    counts: Counter[str] = Counter()
    for page in pages:
        keys = {furniture_key(line.text) for line in edge_lines(page)}
        counts.update(key for key in keys if len(key) >= 3)
    return {key for key, count in counts.items() if count >= MIN_REPEATS}


def strip_edges(page: Page, repeated: set[str]) -> list[Line]:
    """Peel furniture off the top and bottom of the page and return what was removed."""
    removed = []
    for _ in range(MAX_EDGE_LINES):
        if page.lines and is_furniture(page.lines[0], page, repeated):
            removed.append(page.lines.pop(0))
        if page.lines and is_furniture(page.lines[-1], page, repeated):
            removed.append(page.lines.pop())
    return removed


def page_number_offset(removed: dict[int, list[Line]]) -> int | None:
    """How far printed page numbers are from PDF page numbers, if they agree often enough."""
    offsets: Counter[int] = Counter()
    for number, lines in removed.items():
        for line in lines:
            if line.text.isdigit():
                offsets[int(line.text) - number] += 1
    if not offsets:
        return None
    offset, count = offsets.most_common(1)[0]
    return offset if count >= MIN_REPEATS else None


def strip_glued_page_number(page: Page, printed: int) -> None:
    """OCR sometimes puts the page number on the same line as the text next to it."""
    number = str(printed)
    if page.lines and page.lines[-1].text.endswith(" " + number):
        page.lines[-1].text = page.lines[-1].text.removesuffix(number).rstrip()
    if page.lines and page.lines[0].text.startswith(number + " "):
        page.lines[0].text = page.lines[0].text.removeprefix(number).lstrip()


def split_footnotes(page: Page) -> None:
    """Move the footnote block at the bottom of the page from its lines to its footnotes.

    Runs after page numbers are gone, so the footnotes are the last lines. The block
    starts at the highest wide gap in the bottom of the page whose next line opens
    with a reference mark.
    """
    lines = page.lines
    if len(lines) < 3:
        return

    gaps = [below.y0 - above.y1 for above, below in pairwise(lines)]
    usual_gap = max(statistics.median(gaps), 0)
    line_height = statistics.median(line.height for line in lines)
    wide_gap = max(FOOTNOTE_GAP * usual_gap, line_height / 2)

    start = None
    for index in range(len(lines) - 1, 0, -1):
        size = len(lines) - index
        if size > MAX_FOOTNOTE_LINES or size * 4 > len(lines):
            break
        line = lines[index]
        if line.y0 < page.height * FOOTNOTE_AREA:
            break
        if gaps[index - 1] > wide_gap and starts_with_mark(line.text):
            start = index

    if start is not None and not runs_on(lines[-1], lines):
        page.footnotes = lines[start:]
        page.lines = lines[:start]


def runs_on(last: Line, lines: list[Line]) -> bool:
    """A full-width last line broken mid-word continues on the next page.

    Then the block is body text after a section break, such as a numbered section
    starting with "1.", not footnotes.
    """
    full_width = statistics.median(line.x1 - line.x0 for line in lines)
    return last.text.endswith("-") and last.x1 - last.x0 > 0.8 * full_width


def starts_with_mark(text: str) -> bool:
    first, _, rest = text.partition(" ")
    return bool(rest) and FOOTNOTE_MARK.match(first) is not None
