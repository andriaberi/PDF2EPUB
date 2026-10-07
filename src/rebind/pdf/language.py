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
