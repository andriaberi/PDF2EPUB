import re
import statistics
from collections import Counter
from itertools import pairwise

from pdf2epub.labels import label_level, split_label
from pdf2epub.languages import all_words

from .footnotes import marked_footnotes, number_footnotes
from .models import Line, Page
from .text import NOTE_MARK, script_of, strip_edge_debris

MARGIN = 0.12
MAX_EDGE_LINES = 3
MIN_REPEATS = 3
PUNCTUATION = re.compile(r"^\W+|\W+$")
ROMAN = re.compile(r"^[ivxlcdm]+\.?$", re.IGNORECASE)
CHAPTER_NUMBER = re.compile(r"^[IVXLCDM]+\.?$")
NUMBER = re.compile(r"^[\d.,:;/()\[\]–—-]+$")
WORD = re.compile(r"[^\W\d_]{2,}")
NOT_LETTERS = re.compile(r"[\d\W_]+")
SEPARATOR = re.compile(r"^[*⁂•·~=_—–\- ]+$")
WEB = re.compile(
    r"www\.|https?://|\b\w+\.(?:ge|com|org|net|ru)\b|©"
    + "".join(f"|{re.escape(word)}" for word in sorted(all_words("website"))),
    re.IGNORECASE,
)
MAX_CREDIT_WORDS = 6
MAX_CREDIT_LINES = 4
FOOTNOTE_AREA = 0.6
FOOTNOTE_GAP = 3
MAX_FOOTNOTE_LINES = 6

# "79ფილტვების ანთება"
GLUED_MARK = re.compile(r"^\d{1,3}(?=[^\W\d_])")

# OCR reads a raised "¹" as "'!", "%", "31"; a dash opens speech instead.
FOOTNOTE_MARK = re.compile(r"^[\d*†‡§'’\"“”!%^°¹²³⁰⁴-⁹]{1,3}[.)]?$")


def remove_noise(pages: list[Page]) -> list[Page]:
    for page in pages:
        if page.scanned:
            page.lines = drop_junk(page.lines)
        if not any(has_long_word(line.text) for line in page.lines):
            page.lines = []

    for page in pages:
        page.lines = drop_web_credits(page.lines)

    repeated = repeated_edge_lines(pages)
    running = running_labels(pages)
    removed = {page.number: strip_edges(page, repeated, running) for page in pages}

    offset = page_number_offset(removed)
    if offset is not None:
        for page in pages:
            strip_glued_page_number(page, page.number + offset)

    for page in pages:
        drop_footnotes(page)
        if page.scanned:
            for line in page.lines:
                line.text = strip_edge_debris(line.text)
            page.lines = [line for line in page.lines if line.text]

    number_footnotes(pages)
    return pages


def drop_web_credits(lines: list[Line]) -> list[Line]:
    dropped: set[int] = set()
    for index, line in enumerate(lines):
        if not WEB.search(line.text) or len(line.text.split()) > MAX_CREDIT_WORDS:
            continue
        dropped.add(index)
        above = index - 1
        while (
            above >= 0
            and index - above <= MAX_CREDIT_LINES
            and lines[above + 1].y0 - lines[above].y1 < lines[above].height
            and aligned(lines[above], line)
        ):
            dropped.add(above)
            above -= 1
    return [line for index, line in enumerate(lines) if index not in dropped]


def aligned(upper: Line, lower: Line) -> bool:
    return any(
        abs(a - b) < lower.height
        for a, b in [
            (upper.x0, lower.x0),
            (upper.x1, lower.x1),
            (upper.x0 + upper.x1, lower.x0 + lower.x1),
        ]
    )


def drop_junk(lines: list[Line]) -> list[Line]:
    kept = [line for line in lines if not is_junk(line.text)]
    junk = len(lines) - len(kept)
    if junk >= 2 and junk >= len(kept):
        kept = [line for line in kept if has_long_word(line.text)]
    return kept


def is_junk(text: str) -> bool:
    if SEPARATOR.match(text) or NUMBER.match(text) or ROMAN.match(text):
        return False
    text = NOTE_MARK.sub("", text)

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
    scripts = {script_of(c) for c in token if c.isalpha()}
    if len(scripts) != 1:
        return False
    return all(c.isalpha() or c in "'’-." for c in token)


def is_furniture(line: Line, page: Page, repeated: set[str], running: set[str]) -> bool:
    in_margin = line.y1 < page.height * MARGIN or line.y0 > page.height * (1 - MARGIN)
    if not in_margin or CHAPTER_NUMBER.match(line.text.replace(" ", "")):
        return False
    if is_labelled(line.text) and line.text.casefold() not in running:
        return False
    return is_page_number(line.text) or furniture_key(line.text) in repeated


def is_labelled(text: str) -> bool:
    return label_level(text) is not None or split_label(text) is not None


def is_page_number(text: str) -> bool:
    compact = text.replace(" ", "")
    if len(compact) > 8 or CHAPTER_NUMBER.match(compact):
        return False
    if ROMAN.match(compact):
        return True
    return not WORD.search(text)


def furniture_key(text: str) -> str:
    return NOT_LETTERS.sub(" ", text).strip().lower()


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


def running_labels(pages: list[Page]) -> set[str]:
    edges = {
        page.number: {line.text.casefold() for line in edge_lines(page) if is_labelled(line.text)}
        for page in pages
    }
    return {
        text for number, texts in edges.items() for text in texts & edges.get(number + 1, set())
    }


def strip_edges(page: Page, repeated: set[str], running: set[str]) -> list[Line]:
    removed: list[Line] = []
    taken: set[str] = set()

    def peel(index: int) -> None:
        line = page.lines[index]
        key = furniture_key(line.text)
        if (not key or key not in taken) and is_furniture(line, page, repeated, running):
            removed.append(page.lines.pop(index))
            taken.add(key)

    for _ in range(MAX_EDGE_LINES):
        if page.lines:
            peel(0)
        if page.lines:
            peel(-1)
    return removed


def page_number_offset(removed: dict[int, list[Line]]) -> int | None:
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
    number = str(printed)
    if page.lines and page.lines[-1].text.endswith(" " + number):
        page.lines[-1].text = page.lines[-1].text.removesuffix(number).rstrip()
    if page.lines and page.lines[0].text.startswith(number + " "):
        page.lines[0].text = page.lines[0].text.removeprefix(number).lstrip()


def drop_footnotes(page: Page) -> None:
    lines = page.lines
    if len(lines) < 3:
        return

    gaps = [below.y0 - above.y1 for above, below in pairwise(lines)]
    usual_gap = max(statistics.quantiles(gaps, n=4)[0], 0)
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
        page.lines = lines[:start]
        page.footnotes = marked_footnotes(lines[start:], page.lines)


def runs_on(last: Line, lines: list[Line]) -> bool:
    full_width = statistics.median(line.x1 - line.x0 for line in lines)
    return last.text.endswith("-") and last.x1 - last.x0 > 0.8 * full_width


def starts_with_mark(text: str) -> bool:
    if GLUED_MARK.match(text):
        return True
    first, _, rest = text.partition(" ")
    return bool(rest) and FOOTNOTE_MARK.match(first) is not None
