"""The words books put before their division numbers: "თავი მეორე", "Chapter 2"."""

import re

# Division words, outermost first. Georgian: ტომი volume, ნაწილი part, წიგნი book,
# თავი chapter.
LABELS = {
    "ტომი": 1,
    "volume": 1,
    "ნაწილი": 2,
    "part": 2,
    "წიგნი": 3,
    "book": 3,
    "თავი": 4,
    "chapter": 4,
}

# "Chapter 12", "CHAPTER XII.", "თავი მეორე", "მესამე ნაწილი". The number is one
# word because OCR garbles Georgian ordinals too much to spell-check them
# ("მეეჭპვგჭსე"). Only a numeral may take a full stop, so a sentence like
# "თავი დახარა." isn't a label.
LABEL = re.compile(r"^(\w+)\s+(\w+|\d+\.|[IVXLCDM]+\.)$", re.IGNORECASE)


def label_level(text: str) -> int | None:
    """The division level of a label like "თავი მეორე", allowing one OCR misread letter."""
    found = find_label(text)
    return LABELS[found[1]] if found else None


def fix_label(text: str) -> str:
    """Spell the label word right: OCR's "თაჭი მეორე" becomes "თავი მეორე"."""
    found = find_label(text)
    if found is None:
        return text
    index, label = found
    words = text.split()
    word = words[index]
    if word.isupper():
        label = label.upper()
    elif word[0].isupper():
        label = label.capitalize()
    words[index] = label
    return " ".join(words)


def find_label(text: str) -> tuple[int, str] | None:
    """Which word of the line is the label word, and which label it is.

    The label usually comes first ("ნაწილი მესამე") but may follow its number
    ("მესამე ნაწილი"). Second place takes only an exact match: "მისი თავს" is text.
    """
    match = LABEL.match(text)
    if not match:
        return None
    first, second = (word.lower() for word in match.groups())
    for label in LABELS:
        if len(first) == len(label) and sum(a != b for a, b in zip(first, label, strict=True)) <= 1:
            return 0, label
    if second in LABELS:
        return 1, second
    return None
