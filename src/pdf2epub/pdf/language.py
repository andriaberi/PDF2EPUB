from collections import Counter

from .models import Page
from .text import script_of

# The languages PDF2EPUB supports, by the script they're written in.
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
    """The PDF's own language tag, unless the text disagrees on whether it is Georgian,
    as Georgian books tagged "en-US" do. A Latin book tagged "fr" stays French."""
    detected = detect_language(pages)
    if declared is None:
        return detected
    if detected is not None and (declared.split("-")[0].lower() == "ka") != (detected == "ka"):
        return detected
    return declared
