import re

from pdf2epub.languages import LANGUAGES, all_words

LABELS = {
    word: level for language in LANGUAGES.values() for word, level in language.divisions.items()
}

# "Chapter 12", "თავი მეორე", "მესამე ნაწილი"
LABEL = re.compile(r"^(\w+)\s+(\w+|\d+\.|[IVXLCDM]+\.)$", re.IGNORECASE)

# "თავი მეშვიდე ...": a label run into its title
NUMBER_WORDS = [pattern for language in LANGUAGES.values() for pattern in language.words["numbers"]]
NUMBER_WORD = re.compile(
    r"^(\d+\.?|[IVXLCDM]+\.?" + "".join(f"|{pattern}" for pattern in NUMBER_WORDS) + ")$",
    re.IGNORECASE,
)
PREFACE_NAMES = all_words("prefaces")
SECTION_NAMES = PREFACE_NAMES | all_words("sections")
NUMBER_LEVEL = 5
SUBHEADING_LEVEL = 6

# "XII", "XII.", "7", "7."
NUMERAL = re.compile(r"^([IVXLCDM]{1,7}|\d{1,3})\.?$")
ROMAN = [
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"),
    (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
]  # fmt: skip
ROMAN_VALUES = {letter: value for value, letter in ROMAN if len(letter) == 1}


def label_level(text: str) -> int | None:
    found = find_label(text)
    return LABELS[found[1]] if found else None


def fix_label(text: str) -> str:
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
    match = LABEL.match(text)
    if not match:
        return None
    first, second = (word.lower() for word in match.groups())
    for label in LABELS:
        if len(first) == len(label) and sum(a != b for a, b in zip(first, label, strict=True)) <= 1:
            return 0, label
    if second in LABELS and NUMBER_WORD.match(first):
        return 1, second
    return None


def is_section_name(text: str) -> bool:
    return text.strip().casefold() in SECTION_NAMES


def is_preface(text: str) -> bool:
    return text.strip().casefold() in PREFACE_NAMES


def split_label(text: str) -> tuple[str, str] | None:
    words = text.split()
    if len(words) < 3 or words[0].lower() not in LABELS or not NUMBER_WORD.match(words[1]):
        return None
    if text.endswith((".", ",", ";", ":", "!", "?", "…")):
        return None
    title = " ".join(words[2:]).lstrip("-–— ")
    return f"{words[0]} {words[1]}", title


def numeral_value(text: str) -> int | None:
    match = NUMERAL.match(text.strip())
    if not match:
        return None
    number = match.group(1)
    if number.isdigit():
        return int(number) or None
    value = roman_value(number)
    # Well-formed numerals only.
    return value if to_roman(value) == number else None


def roman_value(numeral: str) -> int:
    values = [ROMAN_VALUES[letter] for letter in numeral]
    following = [*values[1:], 0]
    return sum(-v if v < n else v for v, n in zip(values, following, strict=True))


def to_roman(value: int) -> str:
    letters = []
    for amount, letter in ROMAN:
        count, value = divmod(value, amount)
        letters.append(letter * count)
    return "".join(letters)
