import re

from pdf2epub.labels import label_level
from pdf2epub.pdf import Page

# Words a printed table of contents is headed with.
TITLES = {"სარჩევი", "შინაარსი", "contents", "table of contents"}

# "Chapter 3 ........ 45", "თავი მესამე 45": an entry ending in its page number.
ENTRY = re.compile(r"\S.*(\s|\.{2,}|…)\d{1,4}$")

# A page of entries, most of its lines, is a contents page even without its title.
MIN_ENTRIES = 5
ENTRY_SHARE = 0.5

# Under a contents title fewer will do: titles that wrap take up lines between entries.
MIN_TITLED_ENTRIES = 3
TITLED_ENTRY_SHARE = 0.3


def drop_printed_contents(pages: list[Page]) -> list[Page]:
    """Leave out the book's printed table of contents; the EPUB has a working one."""
    return [page for page in pages if not is_contents_page(page)]


def is_contents_page(page: Page) -> bool:
    lines = [line.text.strip() for line in page.lines]
    entries = sum(1 for text in lines if is_entry(text))
    if entries >= MIN_ENTRIES and entries >= ENTRY_SHARE * len(lines):
        return True
    titled = any(text.rstrip(":").casefold() in TITLES for text in lines[:3])
    return titled and entries >= MIN_TITLED_ENTRIES and entries >= TITLED_ENTRY_SHARE * len(lines)


def is_entry(text: str) -> bool:
    """A heading listed with its page number, or a label alone, as some contents list them."""
    return bool(ENTRY.match(text)) or label_level(text) is not None
