import re
import statistics
from difflib import SequenceMatcher

from pdf2epub.labels import LABELS, is_preface
from pdf2epub.paragraphs import Paragraph
from pdf2epub.pdf.text import script_of

from .models import Heading, Section

# Front matter this short is a title page, not a preface.
TITLE_PAGE = 3

# A title page printed again before a later volume may carry an epigraph or the
# translators too, so it may be a little longer.
REPRINTED_TITLE_PAGE = 6

# A note in brackets after the title: "ანა კარენინა (ტომი I)".
BRACKETED = re.compile(r"\s*\([^)]*\)\s*$")

# Georgian letters in Latin, the national romanisation, to compare with metadata
# written in Latin: "ლევ ტოლსტოი" reads "lev tolstoi", close to "Leo Tolstoy".
ROMANISATION = str.maketrans(
    {
        "ა": "a", "ბ": "b", "გ": "g", "დ": "d", "ე": "e", "ვ": "v", "ზ": "z", "თ": "t",
        "ი": "i", "კ": "k", "ლ": "l", "მ": "m", "ნ": "n", "ო": "o", "პ": "p", "ჟ": "zh",
        "რ": "r", "ს": "s", "ტ": "t", "უ": "u", "ფ": "p", "ქ": "k", "ღ": "gh", "ყ": "q",
        "შ": "sh", "ჩ": "ch", "ც": "ts", "ძ": "dz", "წ": "ts", "ჭ": "ch", "ხ": "kh",
        "ჯ": "j", "ჰ": "h",
    }
)  # fmt: skip

# How alike a romanised line and the metadata must be to spell the same name.
SAME_NAME = 0.75

# Title page lines are short; longer ones are sentences.
MAX_NAME_WORDS = 8

# The colophon after the book's last line: at most this many lines, each set far right
# of the text (this many line heights) or naming a year.
MAX_BACK_MATTER = 6
SET_RIGHT = 4
YEAR = re.compile(r"\b(1[5-9]|20)\d\d\b")
# ...or naming who made the book, or closing it: "მთარგმნელი: ...", "დასასრული".
CREDIT = re.compile(r"თარგმ|რედაქტ|გამომცემ|translat|edited|publish", re.IGNORECASE)
THE_END = {"დასასრული", "the end", "end", "fin"}

# Text before the first heading that is more than this share of the book is the book
# itself, its first chapters missed, not a title page or a translator's note.
MAX_FRONT_MATTER = 0.1


def drop_front_matter(sections: list[Section], title: str, author: str | None) -> list[Section]:
    """Leave out the book's own title pages; the EPUB opens with a title page of its own.
    What each step leaves out is marked with its role, so it can be shown if wanted."""
    steps = [
        ("preface", drop_prefaces),
        ("reprint", drop_title_page_reprints),
        ("title-page", lambda kept: drop_repeated_title(kept, title, author)),
        ("front", drop_text_before_first_heading),
        ("back", drop_back_matter),
    ]
    for role, drop in steps:
        before = parts(sections)
        sections = drop(sections)
        kept = {id(part) for part in parts(sections)}
        for part in before:
            if id(part) not in kept:
                part.role = role
    return sections


def drop_back_matter(sections: list[Section]) -> list[Section]:
    """Leave out who translated or published the book, and when, printed after its last
    line: "ინგლისურიდან თარგმნა - მზია კეკელიძემ", "ნოემბერი 1943 - თებერვალი 1944.",
    and "დასასრული"."""
    if not sections:
        return sections
    paragraphs = sections[-1].paragraphs
    lines = [line for paragraph in paragraphs for line in paragraph.lines]
    if not lines:
        return sections
    left = statistics.median(line.x0 for line in lines)
    count = 0
    while count < min(MAX_BACK_MATTER, len(paragraphs) - 1) and is_colophon_line(
        paragraphs[-1 - count], left
    ):
        count += 1
    if count:
        sections[-1].paragraphs = paragraphs[:-count]
    return sections


def is_colophon_line(paragraph: Paragraph, left: float) -> bool:
    if len(paragraph.lines) != 1 or paragraph.text.startswith("["):
        return False
    line = paragraph.lines[0]
    text = paragraph.text
    return (
        line.x0 - left > SET_RIGHT * line.height
        or YEAR.search(text) is not None
        or CREDIT.search(text) is not None
        or text.rstrip(".!").casefold() in THE_END
    )


def parts(sections: list[Section]) -> list[Heading | Paragraph]:
    """The sections' headings and paragraphs in reading order."""
    found: list[Heading | Paragraph] = []
    for section in sections:
        if section.heading:
            found.append(section.heading)
        found.extend(section.paragraphs)
    return found


def drop_prefaces(sections: list[Section]) -> list[Section]:
    """Leave out forewords and prefaces, with any sections under them."""
    kept: list[Section] = []
    preface_level = None
    for section in sections:
        heading = section.heading
        if heading and preface_level is not None and heading.level > preface_level:
            continue
        preface_level = heading.level if heading and is_preface(heading.label) else None
        if preface_level is None:
            kept.append(section)
    return kept


def drop_title_page_reprints(sections: list[Section]) -> list[Section]:
    """Drop the title page printed again before a new volume, at the end of a section.

    The reprint names its own volume, "(ტომი II)" where the first said "(ტომი I)".
    """
    if not sections or sections[0].heading or len(sections[0].paragraphs) > REPRINTED_TITLE_PAGE:
        return sections
    title_page = {reprint_key(p.text) for p in sections[0].paragraphs}
    for section in sections[1:]:
        while section.paragraphs and reprint_key(section.paragraphs[-1].text) in title_page:
            section.paragraphs.pop()
    return sections


def reprint_key(text: str) -> str:
    # One printing may trail off in dot leaders the other leaves out: "თარგმანი. . .. . .".
    return without_volume(text).rstrip(" .…").casefold()


def drop_repeated_title(sections: list[Section], title: str, author: str | None) -> list[Section]:
    """Drop the title and author, which the title page already shows, and the book's
    own title page however it spells them: "ალბერ კამიუ - უცხო"."""
    if not sections or sections[0].heading:
        return sections
    repeated = {title.casefold(), (author or "").casefold()}
    front = sections[0]
    front.paragraphs = [p for p in front.paragraphs if p.text.casefold() not in repeated]
    return sections if front.paragraphs and not is_title_page(front) else sections[1:]


def drop_text_before_first_heading(sections: list[Section]) -> list[Section]:
    """Leave out what comes before the first heading: the printed title page, credits,
    a translator's note. A book without headings keeps all its text."""
    if len(sections) < 2 or sections[0].heading:
        return sections
    front = len(sections[0].paragraphs)
    total = sum(len(section.paragraphs) for section in sections)
    return sections[1:] if front <= MAX_FRONT_MATTER * total else sections


def is_title_page(section: Section) -> bool:
    """A few lines on the first page, names rather than sentences: author, title."""
    paragraphs = section.paragraphs
    return (
        len(paragraphs) <= TITLE_PAGE
        and all(p.page == paragraphs[0].page for p in paragraphs)
        and not any(p.text.endswith((".", "!", "?", "…")) for p in paragraphs)
    )


def title_page_spelling(
    sections: list[Section], title: str | None, author: str | None
) -> tuple[str | None, str | None]:
    """The title and author as the book's title page spells them: "ლევ ტოლსტოი" for
    metadata in Latin letters, "Leo Tolstoy"."""
    if not sections or sections[0].heading:
        return title, author
    lines = [
        without_volume(p.text)
        for p in sections[0].paragraphs
        if len(p.text.split()) <= MAX_NAME_WORDS
    ]
    return same_name(title, lines), same_name(author, lines)


def same_name(name: str | None, lines: list[str]) -> str | None:
    if not name or any(is_georgian(c) for c in name):
        return name
    # Metadata may name the volume too: "Ana karenina II".
    wanted = re.sub(r"\s+[IVX]+$", "", without_volume(name)).casefold()
    best, score = name, SAME_NAME
    for line in lines:
        if not any(is_georgian(c) for c in line):
            continue
        ratio = SequenceMatcher(None, line.translate(ROMANISATION).casefold(), wanted).ratio()
        if ratio >= score:
            best, score = line, ratio
    return best


def without_volume(text: str) -> str:
    """ "ანა კარენინა (ტომი I)" as "ანა კარენინა"."""
    text = text.strip()
    bracketed = BRACKETED.search(text)
    if bracketed and any(label in bracketed.group().casefold() for label in LABELS):
        return text[: bracketed.start()]
    return text


def is_georgian(char: str) -> bool:
    return script_of(char) == "GEORGIAN"
