from .models import Section

# Front matter this short is a title page, not a preface.
TITLE_PAGE = 3

# Text before the first heading that is more than this share of the book is the book
# itself, its first chapters missed, not a title page or a translator's note.
MAX_FRONT_MATTER = 0.1


def drop_front_matter(sections: list[Section], title: str, author: str | None) -> list[Section]:
    """Leave out the book's own title pages; the EPUB opens with a title page of its own."""
    sections = drop_title_page_reprints(sections)
    sections = drop_repeated_title(sections, title, author)
    return drop_text_before_first_heading(sections)


def drop_title_page_reprints(sections: list[Section]) -> list[Section]:
    """Drop the title page printed again before a new volume, at the end of a section."""
    if not sections or sections[0].heading or len(sections[0].paragraphs) > TITLE_PAGE:
        return sections
    title_page = {p.text.casefold() for p in sections[0].paragraphs}
    for section in sections[1:]:
        while section.paragraphs and section.paragraphs[-1].text.casefold() in title_page:
            section.paragraphs.pop()
    return sections


def drop_repeated_title(sections: list[Section], title: str, author: str | None) -> list[Section]:
    """The title page already shows the title and author; don't print them again.

    The PDF often doesn't say what its title is, so the book's own title page goes
    too, however it spells the title ("ალბერ კამიუ - უცხო").
    """
    if not sections or sections[0].heading:
        return sections
    repeated = {title.casefold(), (author or "").casefold()}
    front = sections[0]
    front.paragraphs = [p for p in front.paragraphs if p.text.casefold() not in repeated]
    return sections if front.paragraphs and not is_title_page(front) else sections[1:]


def drop_text_before_first_heading(sections: list[Section]) -> list[Section]:
    """Leave out what comes before the first heading: the printed title page, credits,
    an epigraph, a translator's note.

    A book without headings keeps all its text.
    """
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
