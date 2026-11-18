from collections import Counter

from pdf2epub.languages import LANGUAGES, language

from .models import Page
from .text import script_of

SAMPLE_LINES = 2000
UNKNOWN_SCRIPT = "LATIN"


def detect_language(pages: list[Page]) -> str | None:
    lines = [line.text for page in pages for line in page.lines][:SAMPLE_LINES]
    scripts = Counter(script for text in lines for c in text if (script := script_of(c)))
    if not scripts:
        return None

    script = scripts.most_common(1)[0][0]
    candidates = [found for found in LANGUAGES.values() if found.script == script]
    if len(candidates) <= 1:
        return candidates[0].code if candidates else None
    words = Counter(word.casefold() for text in lines for word in text.split())
    best = max(candidates, key=lambda found: sum(words[w] for w in found.words["common"]))
    return best.code


def book_language(declared: str | None, pages: list[Page]) -> str | None:
    detected = detect_language(pages)
    if declared is None:
        return detected
    if detected is None:
        return declared
    found = language(declared)
    declared_script = found.script if found else UNKNOWN_SCRIPT
    return detected if declared_script != LANGUAGES[detected].script else declared
