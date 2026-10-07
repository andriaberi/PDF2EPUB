import re
import unicodedata

# Ligatures such as "ﬁ" and "ﬂ", which NFC keeps.
LIGATURES = re.compile(r"[\ufb00-\ufb06]")

# Invisible characters that only get in the way.
INVISIBLE = re.compile(r"[\u200b-\u200d\u2060\ufeff\u00ad\x00-\x08\x0b-\x1f\x7f]")

DASHES = "\\-\u2010\u2011\u2012\u2013\u2014\u2015\u2212"

# OCR often reads one dash as two or three ("–-", "-–-", "––").
DASH_RUN = re.compile(f"[{DASHES}]{{2,}}")

# A word broken at the end of the line, whatever dash the PDF used for it.
LINE_END_HYPHEN = re.compile(f"(?<=\\w)[{DASHES}]+$|(?<=\\w)\u00ad$")

# Neither English nor Georgian uses the middle dot; in OCR text it's dust. It can
# stand between two words, so it becomes a space.
STRAY_DOT = re.compile("·")

# OCR reads specks at the edge of the page as lone symbols at the start or end of a
# line: "' ლივრი", "| — მარკიზ", "სახელი. '", "ეტყოდა: |".
EDGE_DEBRIS = re.compile(r"^(?:[\"'|/_+=,:;`]+(?: |$))+|(?: [\"'|/_,:;`]+)+$")

# Georgian quotes are „ and “, so a straight quote or bar stuck to the first
# Georgian letter of a line is a speck too: "'ზოგიერთ", "|ჭზაზე".
GLUED_DEBRIS = re.compile("^[\"'|](?=[\u10d0-\u10ff])")

SPACES = re.compile(r"\s+")

# A heading set letter-spaced, alone on its line with a number or a dash at most:
# "IV წ ი გ ნ ი", "თ ა ლ ე ჲ ა", "C h a p t e r 3". Letter-spaced emphasis inside the text
# stays as printed: it may wrap onto the next line, where a half-joined word reads worse.
LETTER_SPACED = re.compile(
    r"^((?:[^\w\s]+ |(?:\d+|[IVXLCDM]+)\.? )??[^\w\s]*)"  # "IV ", "- ", "„"
    r"([^\W\d_](?: [^\W\d_]){2,})"  # "წ ი გ ნ ი"
    r"([!?“”»\"]*(?: \d+)?)$"  # "!“", " 3"; a heading ends with no full stop or comma
)


def clean_text(text: str) -> str:
    """Normalise one line of PDF text so later steps can compare and join lines."""
    text = unicodedata.normalize("NFC", text)
    text = LIGATURES.sub(lambda m: unicodedata.normalize("NFKC", m.group()), text)
    text = SPACES.sub(" ", text).strip()

    text = LINE_END_HYPHEN.sub("-", text)
    text = INVISIBLE.sub("", text)
    text = DASH_RUN.sub("\u2014", text)
    text = STRAY_DOT.sub(" ", text)
    text = SPACES.sub(" ", text).strip()

    if spaced := LETTER_SPACED.match(text):
        lead, word, end = spaced.groups()
        return lead + word.replace(" ", "") + end
    return text


def strip_edge_debris(text: str) -> str:
    """Remove OCR specks from the start and end of a line; may leave it empty."""
    text = EDGE_DEBRIS.sub("", text)
    return GLUED_DEBRIS.sub("", text).strip()


def script_of(char: str) -> str | None:
    """The Unicode script of a letter ("LATIN", "GEORGIAN", ...), None for anything else."""
    if not char.isalpha():
        return None
    return unicodedata.name(char, "").split(" ", 1)[0] or None
