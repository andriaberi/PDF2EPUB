import re
from itertools import pairwise

from pdf2epub.labels import is_section_name, label_level, numeral_value, split_label
from pdf2epub.pdf import Line, Page, Picture
from pdf2epub.pdf.text import NOTE_MARK, script_of

from .layout import (
    OPENINGS,
    SPEECH_DASHES,
    TITLE_LINES,
    Layout,
    ends_page_early,
    ends_paragraph,
    ends_sentence,
    ends_with_blank_line,
    fit,
    has_gap_before,
    is_indented,
    is_set_apart,
    is_short,
    is_spaced_apart,
    is_tall,
    measure,
    stands_apart,
    starts_with_blank_line,
    text_bottom,
    text_column,
    text_top,
)
from .models import Paragraph, is_scene_break
from .verse import find_verse

# "!", ". დიახ", ", -"; "“" only before a space or punctuation
CLOSES = re.compile(r"^(?:[.!?;:)»](?!\.)|,(?!,)|“(?=[\s.,;:!?)]))")
OPENING_QUOTES = ("„", "«")

# "29. როდესაც ..."
SECTION_NUMBER = re.compile(r"^(\d{1,3})\. ")
CLAUSE_BREAK = re.compile(r"[.,;:]\s")
SET_TITLE_WORDS = 6
SET_TITLE_WIDTH = 0.6
MAX_HEADING_WIDTH = 0.8
TITLE_ENDS = (".", ",", ":", ";", "!", "?", "…", "-", "–", "—", "“", "»", '"', ")")


def build_paragraphs(pages: list[Page]) -> list[Paragraph]:
    paragraphs: list[Paragraph] = []
    previous: tuple[Line, Layout] | None = None
    if not any(page.lines for page in pages):
        return paragraphs
    column = text_column(pages)
    bottom = text_bottom(pages)
    top = text_top(pages)
    apart = False
    section: int | None = None

    texts = [page for page in pages if page.lines]
    for number, page in enumerate(texts):
        layout = fit(measure(page, column.usual_gap), column, page)
        verse = find_verse(page.lines, layout)
        next_page = texts[number + 1].lines if number + 1 < len(texts) else []
        for index, line in enumerate(page.lines):
            above = page.lines[index - 1] if index else None
            following = page.lines[index + 1 :] or next_page
            below = following[0] if following else None
            titled = (
                index not in verse
                and is_set_title(line, previous, below, layout)
                and not (apart and continues_heading(paragraphs[-1], line, above, layout))
            )
            if index in verse:
                starts = verse[index] or not paragraphs or not paragraphs[-1].verse
            elif above is not None and runs_past_picture(above, line, page.pictures):
                starts = False
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
                apart = titled or (
                    above is not None
                    and stands_apart(line, above, layout)
                    and ends_sentence(above.text)
                )
                paragraphs[-1].apart = apart
                paragraphs[-1].after_page_gap = (
                    above is None
                    and previous is not None
                    and after_blank_line(
                        line, layout, page, previous, texts[number - 1], top, bottom
                    )
                )
                if opening := SECTION_NUMBER.match(line.text):
                    section = int(opening.group(1))
            else:
                last = paragraphs[-1]
                if last.verse:
                    last.text = f"{last.text} {line.text}"
                else:
                    last.text = join(last.text, line.text, last.lines[-1].breaks_word)
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
    if previous is not None and (
        breaks_word(previous[0].text)
        or previous[0].breaks_word
        or previous[0].text in SPEECH_DASHES
        or previous[0].text.endswith(OPENING_QUOTES)
    ):
        return False
    if previous is not None and CLOSES.match(line.text):
        return False
    if (
        previous is not None
        and below is not None
        and CLOSES.match(below.text)
        and not ends_sentence(previous[0].text)
        and is_short(line, layout)
    ):
        return False
    if is_scene_break(line.text) or (previous is not None and is_scene_break(previous[0].text)):
        return True
    if is_tall(line, layout) or (previous is not None and is_tall(*previous)):
        return True
    if numeral_value(line.text) or (previous is not None and numeral_value(previous[0].text)):
        return True
    if previous is not None and is_heading_line(*previous):
        return True
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
    return previous is not None and ends_paragraph(*previous)


def after_blank_line(
    line: Line,
    layout: Layout,
    page: Page,
    previous: tuple[Line, Layout],
    before: Page,
    top: float,
    bottom: float,
) -> bool:
    last = previous[0]
    ends_short = ends_with_blank_line(*previous, bottom) and not any(
        picture.y0 >= last.y1 for picture in before.pictures
    )
    starts_low = (
        ends_sentence(last.text)
        and starts_with_blank_line(line, layout, top)
        and not any(picture.y1 <= line.y0 for picture in page.pictures)
    )
    return ends_short or starts_low


def runs_past_picture(above: Line, line: Line, pictures: list[Picture]) -> bool:
    return not ends_sentence(above.text) and any(
        above.y1 <= picture.y0 and picture.y1 <= line.y0 for picture in pictures
    )


def starts_next_section(
    line: Line, previous: tuple[Line, Layout] | None, section: int | None
) -> bool:
    number = SECTION_NUMBER.match(line.text)
    return (
        number is not None
        and previous is not None
        and ends_sentence(previous[0].text)
        and int(number.group(1)) in {1, (section or 0) + 1}
    )


def ends_heading(paragraph: Paragraph, line: Line, layout: Layout) -> bool:
    last = paragraph.lines[-1]
    return (
        len(paragraph.lines) <= TITLE_LINES
        and is_short(last, layout)
        and last.x1 - last.x0 < MAX_HEADING_WIDTH * (layout.right - layout.left)
        and not is_short(line, layout)
    )


def is_glued(word: str) -> bool:
    scripts = {script_of(c) for c in word if c.isalpha()}
    return len(scripts) > 1 and any(c.islower() and script_of(c) == "LATIN" for c in word)


def in_latin_capitals(text: str) -> bool:
    latin = [c for c in text if script_of(c) == "LATIN"]
    return len(latin) >= 2 and all(c.isupper() for c in latin)


def is_set_title(
    line: Line, previous: tuple[Line, Layout] | None, below: Line | None, layout: Layout
) -> bool:
    text = NOTE_MARK.sub("", line.text).strip()
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
        and not has_gap_before(below, line, layout)
        and (not below.text.startswith("(") or in_latin_capitals(text))
    )


def continues_heading(paragraph: Paragraph, line: Line, above: Line | None, layout: Layout) -> bool:
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
    text = line.text
    return is_short(line, layout) and (
        label_level(text) is not None or is_section_name(text) or split_label(text) is not None
    )


def breaks_word(text: str) -> bool:
    return text.endswith("-") and text[-2:-1].isalpha()


def join(text: str, line: str, word_goes_on: bool = False) -> str:
    if breaks_word(text) and line[:1].isalpha():
        return text[:-1] + line
    if word_goes_on and line[:1].isalpha():
        return text + line
    if CLOSES.match(line) or text.endswith(OPENING_QUOTES):
        return text + line
    return f"{text} {line}"


def join_lines(lines: list[Line]) -> str:
    text = lines[0].text
    for above, line in pairwise(lines):
        text = join(text, line.text, above.breaks_word)
    return text


def paragraph_of(lines: list[Line], page: int, epigraph: bool = False) -> Paragraph:
    return Paragraph(join_lines(lines), page, lines, epigraph=epigraph)
