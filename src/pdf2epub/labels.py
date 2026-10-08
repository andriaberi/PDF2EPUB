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
    ("მესამე ნაწილი"). Second place takes only an exact match after a number:
    "მისი თავს" is text.
    """
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


# Sections a book names instead of numbering. They sit at the book's outermost level.
SECTION_NAMES = {
    "წინათქმა",  # foreword
    "წინასიტყვაობა",  # preface
    "წინასიტყვა",  # preface
    "შესავალი",  # introduction
    "პროლოგი",
    "ეპილოგი",
    "ბოლოთქმა",  # afterword
    "foreword",
    "preface",
    "introduction",
    "prologue",
    "epilogue",
    "afterword",
}


# Named sections left out of the EPUB: no one reads them.
PREFACE_NAMES = {"წინათქმა", "წინასიტყვაობა", "წინასიტყვა", "foreword", "preface"}


def is_section_name(text: str) -> bool:
    """A named section's heading: "წინათქმა", "Prologue", "EPILOGUE"."""
    return text.strip().casefold() in SECTION_NAMES


def is_preface(text: str) -> bool:
    """A foreword's or preface's heading: "წინასიტყვაობა", "Preface"."""
    return text.strip().casefold() in PREFACE_NAMES


# The number of a label printed with its title on one line: "თავი მეშვიდე ...".
# Stricter than a label alone, since the line goes on: a numeral, a Georgian
# ordinal or an English number word.
NUMBER_WORD = re.compile(
    r"^(\d+\.?|[IVXLCDM]+\.?|პირველი|მე\w+ე|one|two|three|four|five|six|seven|eight|nine"
    r"|ten|eleven|twelve)$",
    re.IGNORECASE,
)


def split_label(text: str) -> tuple[str, str] | None:
    """A label and its title printed on one line: "თავი მეშვიდე გასეირნება სანაპიროზე",
    "თავი მეექვსე - FONTIS". The title is empty when only a dash follows the label.

    The label word must be spelled right and come first, and the line must not end
    a sentence, so a sentence like "თავი მეორედ დახარა." stays text.
    """
    words = text.split()
    if len(words) < 3 or words[0].lower() not in LABELS or not NUMBER_WORD.match(words[1]):
        return None
    if text.endswith((".", ",", ";", ":", "!", "?", "…")):
        return None
    title = " ".join(words[2:]).lstrip("-–— ")
    return f"{words[0]} {words[1]}", title


# Chapters numbered without a label word sit below every labelled division.
NUMBER_LEVEL = 5

# Headings named but not numbered, set in a chapter's text, sit below them all.
SUBHEADING_LEVEL = 6

# A chapter number alone on its line: "XII", "XII.", "7", "7.". Roman numerals are
# upper case only, so a stray "i" or "v" is never one.
NUMERAL = re.compile(r"^([IVXLCDM]{1,7}|\d{1,3})\.?$")

ROMAN = [
    (1000, "M"),
    (900, "CM"),
    (500, "D"),
    (400, "CD"),
    (100, "C"),
    (90, "XC"),
    (50, "L"),
    (40, "XL"),
    (10, "X"),
    (9, "IX"),
    (5, "V"),
    (4, "IV"),
    (1, "I"),
]


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
    values = [next(value for value, letter in ROMAN if letter == c) for c in numeral]
    total = 0
    for index, value in enumerate(values):
        following = values[index + 1] if index + 1 < len(values) else 0
        total += -value if value < following else value
    return total


def to_roman(value: int) -> str:
    letters = []
    for amount, letter in ROMAN:
        count, value = divmod(value, amount)
        letters.append(letter * count)
    return "".join(letters)
