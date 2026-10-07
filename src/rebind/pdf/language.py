from collections import Counter

from .models import Page
from .text import script_of

# The languages Rebind supports, by the script they're written in.
SCRIPT_LANGUAGES = {"GEORGIAN": "ka", "LATIN": "en"}

SAMPLE_LINES = 2000


def detect_language(pages: list[Page]) -> str | None:
    """Georgian or English, by the script most of the text is in; None for anything else."""
    lines = [line.text for page in pages for line in page.lines][:SAMPLE_LINES]
    scripts = Counter(script for text in lines for c in text if (script := script_of(c)))
    if not scripts:
        return None

    script = scripts.most_common(1)[0][0]
    return SCRIPT_LANGUAGES.get(script)


def book_language(declared: str | None, pages: list[Page]) -> str | None:
    """The PDF's own language tag, unless its text says otherwise.

    PDFs made on an English system tag Georgian books "en-US". Detection tells only
    Georgian from Latin script, so it overrides a tag only when they disagree on
    that: a book tagged "fr" in Latin letters stays French.
    """
    detected = detect_language(pages)
    if declared is None:
        return detected
    if detected is not None and (declared.split("-")[0].lower() == "ka") != (detected == "ka"):
        return detected
    return declared
