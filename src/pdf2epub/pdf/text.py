import re
import unicodedata

# Ligatures NFC keeps: "ﬁ", "ﬂ".
LIGATURES = re.compile(r"[\ufb00-\ufb06]")
INVISIBLE = re.compile(r"[\u200b-\u200d\u2060\ufeff\u00ad\x00-\x08\x0b-\x1f\x7f\ue000-\uf8ff]")
DASHES = "\\-\u2010\u2011\u2012\u2013\u2014\u2015\u2212"

# "–-", "-–-", "––"
DASH_RUN = re.compile(f"[{DASHES}]{{2,}}")
LINE_END_HYPHEN = re.compile(f"(?<=\\w)[{DASHES}]+$|(?<=\\w)\u00ad$")
STRAY_DOT = re.compile("·")
EDGE_DEBRIS = re.compile(r"^(?:[\"'|/_+=,:;`]+(?: |$))+|(?: [\"'|/_,:;`]+)+$")
GLUED_DEBRIS = re.compile("^[\"'|](?=[\u10d0-\u10ff])")
SPACES = re.compile(r"\s+")

# "ფრეილინა[1]"
NOTE_MARK = re.compile(r"\[(\d+)\]")

# "pneumonia⁅79⁆", "word⁅*⁆"
RAISED_OPEN, RAISED_CLOSE = "⁅", "⁆"
RAISED_MARK = re.compile(rf"{RAISED_OPEN}(\d+|[*†‡]+){RAISED_CLOSE}")

# "IV წ ი გ ნ ი", "C h a p t e r 3"
LETTER_SPACED = re.compile(
    r"^((?:[^\w\s]+ |(?:\d+|[IVXLCDM]+)\.? )??[^\w\s]*)"  # "IV ", "- ", "„"
    r"([^\W\d_](?: [^\W\d_]){2,})"  # "წ ი გ ნ ი"
    r"([!?“”»\"]*(?: \d+)?)$"  # "!“", " 3"
)


def clean_text(text: str) -> str:
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
    text = EDGE_DEBRIS.sub("", text)
    return GLUED_DEBRIS.sub("", text).strip()


def script_of(char: str) -> str | None:
    if not char.isalpha():
        return None
    return unicodedata.name(char, "").split(" ", 1)[0] or None
