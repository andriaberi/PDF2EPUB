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

# "Chapter 12", "თავი მეორე", "მესამე ნაწილი": any one word as the number, since OCR
# garbles ordinals. Only a numeral takes a full stop: "თავი დახარა." is text.
LABEL = re.compile(r"^(\w+)\s+(\w+|\d+\.|[IVXLCDM]+\.)$", re.IGNORECASE)

# The number of a label run into its title, "თავი მეშვიდე ...": stricter than a
# label alone, a numeral, a Georgian ordinal or an English number word.
NUMBER_WORD = re.compile(
    r"^(\d+\.?|[IVXLCDM]+\.?|პირველი|მე\w+ე|one|two|three|four|five|six|seven|eight|nine"
    r"|ten|eleven|twelve)$",
    re.IGNORECASE,
)

# Named sections the EPUB leaves out unless asked: forewords and prefaces.
PREFACE_NAMES = {"წინათქმა", "წინასიტყვაობა", "წინასიტყვა", "foreword", "preface"}

# Sections a book names instead of numbering. They sit at the book's outermost level.
SECTION_NAMES = PREFACE_NAMES | {
    "შესავალი",  # introduction
    "პროლოგი",
    "ეპილოგი",
    "ბოლოთქმა",  # afterword
    "introduction",
    "prologue",
    "epilogue",
    "afterword",
}

# Chapters numbered without a label word sit below every labelled division.
NUMBER_LEVEL = 5

# Headings named but not numbered, set in a chapter's text, sit below them all.
SUBHEADING_LEVEL = 6

# A chapter number alone on its line: "XII", "XII.", "7", "7.". Roman numerals are
# upper case only, so a stray "i" or "v" is never one.
NUMERAL = re.compile(r"^([IVXLCDM]{1,7}|\d{1,3})\.?$")

ROMAN = [
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"),
    (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
]  # fmt: skip
ROMAN_VALUES = {letter: value for value, letter in ROMAN if len(letter) == 1}


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
    """Which word is the label word, and which label: first ("ნაწილი მესამე"), or second
    if spelled exactly after a number ("მესამე ნაწილი", but "მისი თავს" is text)."""
    match = LABEL.match(text)
    if not match:
        return None
    first, second = (word.lower() for word in match.groups())
    for label in LABELS:
        if len(first) == len(label) and sum(a != b for a, b in zip(first, label, strict=True)) <= 1:
            return 0, label
    # "სიყვარულის წიგნი", the book of love, names a book rather than numbering one.
    if second in LABELS and NUMBER_WORD.match(first):
        return 1, second
    return None


def is_section_name(text: str) -> bool:
    """A named section's heading: "წინათქმა", "Prologue", "EPILOGUE"."""
    return text.strip().casefold() in SECTION_NAMES


def is_preface(text: str) -> bool:
    """A foreword's or preface's heading: "წინასიტყვაობა", "Preface"."""
    return text.strip().casefold() in PREFACE_NAMES


def split_label(text: str) -> tuple[str, str] | None:
    """A label and its title on one line, "თავი მეექვსე - FONTIS": the label first and
    spelled right, ending no sentence ("თავი მეორედ დახარა." is text)."""
    words = text.split()
    if len(words) < 3 or words[0].lower() not in LABELS or not NUMBER_WORD.match(words[1]):
        return None
    if text.endswith((".", ",", ";", ":", "!", "?", "…")):
        return None
    title = " ".join(words[2:]).lstrip("-–— ")
    return f"{words[0]} {words[1]}", title


def numeral_value(text: str) -> int | None:
    """The number of a lone chapter number like "XII" or "7.", or None for anything else."""
    match = NUMERAL.match(text.strip())
    if not match:
        return None
    number = match.group(1)
    if number.isdigit():
        return int(number) or None
    value = roman_value(number)
    # Only well-formed numerals: "IIII" or "IC" are letters, not numbers.
    return value if to_roman(value) == number else None


def roman_value(numeral: str) -> int:
    """A letter worth less than the next is taken off: "IX" is 9."""
    values = [ROMAN_VALUES[letter] for letter in numeral]
    return sum(
        -v if v < following else v for v, following in zip(values, [*values[1:], 0], strict=True)
    )


def to_roman(value: int) -> str:
    letters = []
    for amount, letter in ROMAN:
        count, value = divmod(value, amount)
        letters.append(letter * count)
    return "".join(letters)
