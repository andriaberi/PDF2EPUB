import re
import statistics
from difflib import SequenceMatcher

from pdf2epub.labels import LABELS, is_preface
from pdf2epub.languages import LANGUAGES, all_words, any_of
from pdf2epub.paragraphs import Paragraph

from .models import Heading, Section

TITLE_PAGE = 3
REPRINTED_TITLE_PAGE = 6
BRACKETED = re.compile(r"\s*\([^)]*\)\s*$")
ROMANISED = {k: v for language in LANGUAGES.values() for k, v in language.romanisation.items()}
ROMANISATION = str.maketrans(ROMANISED)
SAME_NAME = 0.75
MAX_NAME_WORDS = 8
MAX_BACK_MATTER = 6
SET_RIGHT = 4
YEAR = re.compile(r"\b(1[5-9]|20)\d\d\b")
CREDIT = re.compile(any_of(all_words("credits")), re.IGNORECASE)
THE_END = all_words("the_end")
MAX_FRONT_MATTER = 0.1


def drop_front_matter(sections: list[Section], title: str, author: str | None) -> list[Section]:
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


def parts(sections: list[Section]) -> list[Heading | Paragraph]:
    found: list[Heading | Paragraph] = []
    for section in sections:
        if section.heading:
            found.append(section.heading)
        found.extend(section.paragraphs)
    return found


def drop_prefaces(sections: list[Section]) -> list[Section]:
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
    if not sections or sections[0].heading or len(sections[0].paragraphs) > REPRINTED_TITLE_PAGE:
        return sections
    title_page = {reprint_key(p.text) for p in sections[0].paragraphs}
    for section in sections[1:]:
        while section.paragraphs and reprint_key(section.paragraphs[-1].text) in title_page:
            section.paragraphs.pop()
    return sections


def reprint_key(text: str) -> str:
    return without_volume(text).rstrip(" .…").casefold()


def drop_repeated_title(sections: list[Section], title: str, author: str | None) -> list[Section]:
    if not sections or sections[0].heading:
        return sections
    repeated = {title.casefold(), (author or "").casefold()}
    front = sections[0]
    front.paragraphs = [p for p in front.paragraphs if p.text.casefold() not in repeated]
    return sections if front.paragraphs and not is_title_page(front) else sections[1:]


def drop_text_before_first_heading(sections: list[Section]) -> list[Section]:
    if len(sections) < 2 or sections[0].heading:
        return sections
    front = len(sections[0].paragraphs)
    total = sum(len(section.paragraphs) for section in sections)
    return sections[1:] if front <= MAX_FRONT_MATTER * total else sections


def drop_back_matter(sections: list[Section]) -> list[Section]:
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


def is_title_page(section: Section) -> bool:
    paragraphs = section.paragraphs
    return (
        len(paragraphs) <= TITLE_PAGE
        and all(p.page == paragraphs[0].page for p in paragraphs)
        and not any(p.text.endswith((".", "!", "?", "…")) for p in paragraphs)
    )


def title_page_spelling(
    sections: list[Section], title: str | None, author: str | None
) -> tuple[str | None, str | None]:
    if not sections or sections[0].heading:
        return title, author
    lines = [
        without_volume(p.text)
        for p in sections[0].paragraphs
        if len(p.text.split()) <= MAX_NAME_WORDS
    ]
    return same_name(title, lines), same_name(author, lines)


def same_name(name: str | None, lines: list[str]) -> str | None:
    if not name or is_romanisable(name):
        return name
    wanted = re.sub(r"\s+[IVX]+$", "", without_volume(name)).casefold()
    best, score = name, SAME_NAME
    for line in lines:
        if not is_romanisable(line):
            continue
        ratio = SequenceMatcher(None, line.casefold().translate(ROMANISATION), wanted).ratio()
        if ratio >= score:
            best, score = line, ratio
    return best


def without_volume(text: str) -> str:
    text = text.strip()
    bracketed = BRACKETED.search(text)
    if bracketed and any(label in bracketed.group().casefold() for label in LABELS):
        return text[: bracketed.start()]
    return text


def is_romanisable(text: str) -> bool:
    return any(c in ROMANISED for c in text.casefold())
