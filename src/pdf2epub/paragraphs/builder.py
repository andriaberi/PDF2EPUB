import re

from pdf2epub.labels import is_section_name, label_level, numeral_value, split_label
from pdf2epub.pdf import Line, Page
from pdf2epub.pdf.text import script_of

from .layout import (
    OPENINGS,
    TITLE_LINES,
    Layout,
    ends_page_early,
    ends_paragraph,
    ends_sentence,
    fit,
    has_gap_before,
    is_indented,
    is_set_apart,
    is_short,
    is_spaced_apart,
    is_tall,
    measure,
    stands_apart,
    text_column,
)
from .models import Paragraph, is_scene_break
from .verse import find_verse


def build_paragraphs(pages: list[Page]) -> list[Paragraph]:
    """Join the lines of all pages into paragraphs, across page breaks too."""
    paragraphs: list[Paragraph] = []
    previous: tuple[Line, Layout] | None = None
    if not any(page.lines for page in pages):
        return paragraphs
    column = text_column(pages)
    # The paragraph started far below the text above it: it may be a heading.
    apart = False
    # The number of the last numbered section started: "28. ...".
    section: int | None = None

    texts = [page for page in pages if page.lines]
    for number, page in enumerate(texts):
        layout = fit(measure(page), column, page)
        verse = find_verse(page.lines, layout)
        next_page = texts[number + 1].lines if number + 1 < len(texts) else []
        for index, line in enumerate(page.lines):
            above = page.lines[index - 1] if index else None
            following = page.lines[index + 1 :] or next_page
            below = following[0] if following else None
            # A heading set in the text with no space around it, as a line of its own,
            # unless it goes on a heading already started: "გაალმასება." / "და კიდევ ...".
            titled = (
                index not in verse
                and is_set_title(line, previous, below, layout)
                and not (apart and continues_heading(paragraphs[-1], line, above, layout))
            )
            if index in verse:
                # Verse goes on line by line until a stanza ends; text never joins it.
                starts = verse[index] or not paragraphs or not paragraphs[-1].verse
            else:
                heading = paragraphs[-1] if apart else None
                starts = (
                    not paragraphs
                    or paragraphs[-1].verse
                    or titled
                    or starts_next_section(line, previous, section)
                    or starts_paragraph(line, above, layout, previous, heading, below)
                )
            if starts:
                paragraphs.append(Paragraph(line.text, page.number, [line], index in verse))
                # After a chapter's text, not its label: a title follows a finished sentence.
                apart = titled or (
                    above is not None
                    and stands_apart(line, above, layout)
                    and ends_sentence(above.text)
                )
                paragraphs[-1].apart = apart
                if opening := SECTION_NUMBER.match(line.text):
                    section = int(opening.group(1))
            else:
                last = paragraphs[-1]
                last.text = f"{last.text} {line.text}" if last.verse else join(last.text, line.text)
                last.lines.append(line)
            previous = (line, layout)

    return paragraphs


def starts_paragraph(
    line: Line,
    above: Line | None,
    layout: Layout,
    previous: tuple[Line, Layout] | None,
    heading: Paragraph | None = None,
    below: Line | None = None,
) -> bool:
    """`heading` is the paragraph so far when it started far below the text: maybe a heading."""
    # A word broken at the end of the last line always carries on, whatever the layout,
    # and so does the speech after a dialogue dash printed on a line of its own, or a
    # quote opened at the end of the line: "სიტყვა „აღსდგა“ - „" / "Redivivus".
    if previous is not None and (
        breaks_word(previous[0].text)
        or previous[0].text in DASHES
        or previous[0].text.endswith(OPENING_QUOTES)
    ):
        return False
    # A line opening with a full stop or a comma ends the sentence of the line before:
    # "Est modus in rebus" / ". დიახ, სადილსაც...".
    if previous is not None and CLOSES.match(line.text):
        return False
    # Some books set a foreign word mid-sentence on a line of its own, indented as if
    # it started a paragraph: "...უნდა ჰქონდეს" / "Est modus in rebus" / ". დიახ".
    if (
        previous is not None
        and below is not None
        and CLOSES.match(below.text)
        and not ends_sentence(previous[0].text)
        and is_short(line, layout)
    ):
        return False
    # A scene break stands alone, and the text after it starts afresh.
    if is_scene_break(line.text) or (previous is not None and is_scene_break(previous[0].text)):
        return True
    # A heading in a bigger font stands alone: the gap below a tall line measures
    # small, so the gap rule alone would glue the heading to the text after it.
    if is_tall(line, layout) or (previous is not None and is_tall(*previous)):
        return True
    # So does a chapter number alone on its line ("XII", "7."), whatever its size.
    if numeral_value(line.text) or (previous is not None and numeral_value(previous[0].text)):
        return True
    # Text after a label or a named section starts afresh, even with no gap between.
    if previous is not None and is_heading_line(*previous):
        return True
    # A line set apart from the text, like a right-aligned label, stands alone too,
    # even at the foot of a page.
    if previous is not None and is_set_apart(previous[0], line, layout):
        return True
    if is_indented(line, layout):
        return True
    if above is not None and (
        has_gap_before(line, above, layout) or is_spaced_apart(line, above, layout)
    ):
        return True
    if above is None and previous is not None and ends_page_early(*previous):
        return True
    if heading is not None and ends_heading(heading, line, layout):
        return True
    if heading is not None and continues_heading(heading, line, above, layout):
        return False
    # A short line ending a sentence closes its paragraph even when the next line's
    # indent is lost. It also decides whether a page's first line carries on the last
    # page's paragraph.
    return previous is not None and ends_paragraph(*previous)


DASHES = {"-", "–", "—"}

# Punctuation that closes what came before, never opens a line: "!", ". დიახ", ", -".
# Not "…" or "...", which may open one, nor ",,", typed for the opening „. "“" opens
# quotes in English, so it closes only when a space or punctuation follows it, as
# Georgian's closing quote does: "“ უწოდა", "“; პიე".
CLOSES = re.compile(r"^(?:[.!?;:)»](?!\.)|,(?!,)|“(?=[\s.,;:!?)]))")

OPENING_QUOTES = ("„", "«")

# A numbered section's opening: "29. როდესაც კროჲსოსმა ...".
SECTION_NUMBER = re.compile(r"^(\d{1,3})\. ")

# Note marks at the end of a line: "...mon cher, taut miux.[10]".
NOTE_MARKS = re.compile(r"\[\d+\]")

# Punctuation inside a line of text, not a heading: "მან ჟურნალ", "ოსტატი, იტალიური".
CLAUSE_BREAK = re.compile(r"[.,;:]\s")

# A heading set in the text is a few words, well short of the line.
SET_TITLE_WORDS = 6
SET_TITLE_WIDTH = 0.6

# A heading run into the text ends well short of the margin, at most this share of
# the column; a paragraph's first line stops only a word or two short.
MAX_HEADING_WIDTH = 0.8

# A line ending in these is a clause or a sentence, not a heading set in the text.
TITLE_ENDS = (".", ",", ":", ";", "!", "?", "…", "-", "–", "—", "“", "»", '"', ")")


def starts_next_section(
    line: Line, previous: tuple[Line, Layout] | None, section: int | None
) -> bool:
    """The next numbered section, "29. როდესაც ...", after section 28's last sentence.

    Some books number their sections and set them apart only by space, which a page
    break hides, or not at all.
    """
    number = SECTION_NUMBER.match(line.text)
    return (
        number is not None
        and previous is not None
        and ends_sentence(previous[0].text)
        and int(number.group(1)) in {1, (section or 0) + 1}
    )


def ends_heading(paragraph: Paragraph, line: Line, layout: Layout) -> bool:
    """A heading set apart above but run straight into the text below it.

    It is a line or a few, the last one well short of the margin, and the text below
    starts with a full line: "ტინაპელებთან ცხოვრებისა და ... / ამბავი" then the
    chapter's text, on the same page or the next. A paragraph's first line stopping
    a few words short is not one: "3. შემდეგ, როდესაც ჰისტიაჲოსს ... თუ რატომ".
    """
    last = paragraph.lines[-1]
    return (
        len(paragraph.lines) <= TITLE_LINES
        and is_short(last, layout)
        and last.x1 - last.x0 < MAX_HEADING_WIDTH * (layout.right - layout.left)
        and not is_short(line, layout)
    )


def is_glued(word: str) -> bool:
    """Two words of two scripts glued together, "სხვაHybris", as at a quote's edge.

    Capitals amid Georgian are a title typed in the wrong keyboard layout, as the
    book prints it: "OPERATIონეშ".
    """
    scripts = {script_of(c) for c in word if c.isalpha()}
    return len(scripts) > 1 and any(c.islower() and script_of(c) == "LATIN" for c in word)


def in_latin_capitals(text: str) -> bool:
    """Its Latin letters, two or more, all capitals: "OPERATIონეშ შპIღIთუალეშ" as printed."""
    latin = [c for c in text if script_of(c) == "LATIN"]
    return len(latin) >= 2 and all(c.isupper() for c in latin)


def is_set_title(
    line: Line, previous: tuple[Line, Layout] | None, below: Line | None, layout: Layout
) -> bool:
    """A short heading set flush left between two paragraphs, with no space around it.

    "ჰიპე", "დიდი გამოთაყვანება": a few words with no closing punctuation, after a
    finished sentence and before a full line of text.
    """
    text = NOTE_MARKS.sub("", line.text).strip()
    return (
        not layout.indents
        and previous is not None
        and ends_sentence(previous[0].text)
        and not is_indented(line, layout)
        and line.x1 - line.x0 < SET_TITLE_WIDTH * (layout.right - layout.left)
        and len(text.split()) <= SET_TITLE_WORDS
        and not text.endswith(TITLE_ENDS)
        and not text.startswith((*OPENINGS, "("))
        and not CLAUSE_BREAK.search(text)
        and not any(is_glued(word) for word in text.split())
        and below is not None
        and not is_short(below, layout)
        # It runs straight into the text: a stray word before a paragraph's space isn't
        # a heading, "ჰეფაჲსტოსის" / "152. ადრე ეს ფსმეტიქოსი ...".
        and not has_gap_before(below, line, layout)
        # A bracketed translation goes on the text, "(პირველქმნილი მატერია (ლათ.).)",
        # unless it translates a heading in capitals: "OPERATIONES SPIRITUALES".
        and (not below.text.startswith("(") or in_latin_capitals(text))
    )


def continues_heading(paragraph: Paragraph, line: Line, above: Line | None, layout: Layout) -> bool:
    """A heading's next short line, close below: "გაალმასება." / "და კიდევ ერთი ... რამ"."""
    return (
        above is not None
        and len(paragraph.lines) < TITLE_LINES
        and is_short(above, layout)
        and is_short(line, layout)
        and not stands_apart(line, above, layout)
        and not has_gap_before(line, above, layout)
        and not line.text.startswith(OPENINGS)
    )


def is_heading_line(line: Line, layout: Layout) -> bool:
    """A short line reading "თავი მეორე", "წინათქმა", or a label with its title."""
    text = line.text
    return is_short(line, layout) and (
        label_level(text) is not None or is_section_name(text) or split_label(text) is not None
    )


def breaks_word(text: str) -> bool:
    return text.endswith("-") and text[-2:-1].isalpha()


def join(text: str, line: str) -> str:
    """Add a line to a paragraph, rejoining a word broken by a hyphen."""
    if breaks_word(text) and line[:1].isalpha():
        return text[:-1] + line
    if CLOSES.match(line) or text.endswith(OPENING_QUOTES):
        return text + line
    return f"{text} {line}"
