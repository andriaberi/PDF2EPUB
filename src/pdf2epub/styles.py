"""Italics and bold, kept in a block's text as <i> and <b> tags: "a <i>very</i> good day"."""

import re
from difflib import SequenceMatcher
from itertools import groupby

from pdf2epub.pdf import Line
from pdf2epub.pdf.models import BOLD, ITALIC

# The tags as the EPUB's escaped text has them, "&lt;i&gt;", and what each becomes.
ESCAPED_TAG = re.compile(r"&lt;(/?)([ib])&gt;")
ELEMENTS = {ITALIC: "em", BOLD: "strong"}


def styled_text(text: str, lines: list[Line]) -> str:
    """The text with the italics and bold of the printed lines it was made of, as tags.

    The text differs from the lines here and there: words rejoined, marks put in,
    letters cleaned up. A letter takes the style of the printed one it matches, and one
    matching none takes the style on both sides of it, if they agree.
    """
    if not any(line.runs for line in lines):
        return text
    printed: list[tuple[str, str]] = []
    for line in lines:
        printed += [(char, style) for run, style in line.runs or [(line.text, "")] for char in run]
        printed.append(("\n", ""))
    matcher = SequenceMatcher(None, text, "".join(char for char, _ in printed), autojunk=False)
    matched: list[str | None] = [None] * len(text)
    for start, at, size in matcher.get_matching_blocks():
        for offset in range(size):
            matched[start + offset] = printed[at + offset][1]

    # The style of the nearest matched letter on each side.
    left, right = nearest(matched), nearest(matched[::-1])[::-1]
    styles = [
        style if style is not None else (left[index] if left[index] == right[index] else "")
        for index, style in enumerate(matched)
    ]
    return tagged(text, styles)


def nearest(matched: list[str | None]) -> list[str]:
    """For each letter, the style of the last matched one up to it."""
    found, last = [], ""
    for style in matched:
        if style is not None:
            last = style
        found.append(last)
    return found


def tagged(text: str, styles: list[str]) -> str:
    """The text with each styled run in tags, the spaces at its ends left outside."""
    parts = []
    at = 0
    for style, group in groupby(styles):
        size = len(list(group))
        run = text[at : at + size]
        at += size
        core = run.strip()
        if not style or not core:
            parts.append(run)
            continue
        lead, trail = run[: len(run) - len(run.lstrip())], run[len(run.rstrip()) :]
        opening = "".join(f"<{kind}>" for kind in style)
        closing = "".join(f"</{kind}>" for kind in reversed(style))
        parts.append(f"{lead}{opening}{core}{closing}{trail}")
    return "".join(parts)


def styled_html(html: str) -> str:
    """Escaped text with its style tags made HTML, each closed: a tag an edit left open
    closes at the end, and one closing nothing is dropped."""
    parts: list[str] = []
    open_: list[str] = []
    at = 0
    for tag in ESCAPED_TAG.finditer(html):
        parts.append(html[at : tag.start()])
        at = tag.end()
        closing, kind = tag.groups()
        if not closing and kind not in open_:
            open_.append(kind)
            parts.append(f"<{ELEMENTS[kind]}>")
        elif closing and kind in open_:
            # Close what was opened inside it, and open that again after.
            inside = open_[open_.index(kind) + 1 :]
            parts += [f"</{ELEMENTS[k]}>" for k in reversed(inside)]
            parts.append(f"</{ELEMENTS[kind]}>")
            parts += [f"<{ELEMENTS[k]}>" for k in inside]
            open_.remove(kind)
    parts.append(html[at:])
    parts += [f"</{ELEMENTS[kind]}>" for kind in reversed(open_)]
    return "".join(parts)
