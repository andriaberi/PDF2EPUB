import re

from pdf2epub.labels import label_level
from pdf2epub.languages import all_words
from pdf2epub.paragraphs import Paragraph
from pdf2epub.pdf import Page

TITLES = all_words("contents_titles")

# "Chapter 3 ........ 45"
ENTRY = re.compile(r"\S.*(\s|\.{2,}|…)\d{1,4}$")
MIN_ENTRIES = 5
ENTRY_SHARE = 0.5
MIN_TITLED_ENTRIES = 3
TITLED_ENTRY_SHARE = 0.3


def drop_printed_contents(pages: list[Page]) -> list[Page]:
    contents = contents_pages(pages)
    return [page for page in pages if page.number not in contents]


def printed_contents(pages: list[Page]) -> list[Paragraph]:
    contents = contents_pages(pages)
    return [
        Paragraph(
            " ".join(line.text for line in page.lines),
            page.number,
            page.lines,
            verse=True,
            role="contents",
        )
        for page in pages
        if page.lines and page.number in contents
    ]


def contents_pages(pages: list[Page]) -> set[int]:
    found: set[int] = set()
    for page in pages:
        lines = [line.text.strip() for line in page.lines]
        carried = page.number - 1 in found and sum(map(is_entry, lines)) >= ENTRY_SHARE * len(lines)
        if is_contents_page(page) or (lines and carried):
            found.add(page.number)
    return found


def is_contents_page(page: Page) -> bool:
    lines = [line.text.strip() for line in page.lines]
    entries = sum(1 for text in lines if is_entry(text))
    if entries >= MIN_ENTRIES and entries >= ENTRY_SHARE * len(lines):
        return True
    titled = any(text.rstrip(":").casefold() in TITLES for text in lines[:3])
    return titled and entries >= MIN_TITLED_ENTRIES and entries >= TITLED_ENTRY_SHARE * len(lines)


def is_entry(text: str) -> bool:
    return bool(ENTRY.match(text)) or label_level(text) is not None
