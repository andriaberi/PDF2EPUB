"""The words books are read with, one file per language: ka.toml, en.toml. A new file is
a new language, detected by its script."""

import re
import tomllib
from dataclasses import dataclass
from importlib.resources import files
from importlib.resources.abc import Traversable

DIVISIONS = ("volume", "part", "book", "chapter")  # outermost first
FALLBACK = "en"
WORD_LISTS = (
    "common",
    "numbers",
    "prefaces",
    "sections",
    "contents_titles",
    "notes_titles",
    "page_abbreviations",
    "credits",
    "the_end",
    "website",
)
HEADINGS = ("contents", "notes")


class LanguageFileError(ValueError):
    pass


@dataclass(frozen=True)
class Language:
    code: str
    name: str
    script: str  # as pdf.text.script_of names it: "GEORGIAN"
    words: dict[str, list[str]]
    divisions: dict[str, int]  # label word: level
    headings: dict[str, str]
    romanisation: dict[str, str]


def read_language(code: str, text: str) -> Language:
    def fail(problem: str) -> LanguageFileError:
        return LanguageFileError(f"{code}.toml: {problem}")

    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise fail(str(error)) from error
    fields = {"name", "script", *WORD_LISTS, "divisions", "headings", "romanisation"}
    if missing := fields - data.keys():
        raise fail(f"missing {', '.join(sorted(missing))}")
    if unknown := data.keys() - fields:
        raise fail(f"unknown {', '.join(sorted(unknown))}")

    words = {}
    for field in WORD_LISTS:
        values = data[field]
        if not isinstance(values, list) or not all(isinstance(v, str) and v for v in values):
            raise fail(f"{field} should be a list of text")
        # Numbers are regular expressions, the rest words.
        words[field] = values if field == "numbers" else [v.casefold() for v in values]
    for pattern in words["numbers"]:
        try:
            re.compile(pattern)
        except re.error as error:
            raise fail(f"numbers: {pattern!r}: {error}") from error

    if set(data["divisions"]) != set(DIVISIONS):
        raise fail(f"divisions should be {', '.join(DIVISIONS)}")
    divisions = {
        word.casefold(): level
        for level, division in enumerate(DIVISIONS, start=1)
        for word in data["divisions"][division]
    }
    if set(data["headings"]) != set(HEADINGS):
        raise fail(f"headings should be {', '.join(HEADINGS)}")
    if not all(len(letter) == 1 for letter in data["romanisation"]):
        raise fail("romanisation should be single letters")

    return Language(
        code,
        data["name"],
        data["script"],
        words,
        divisions,
        data["headings"],
        data["romanisation"],
    )


def read_languages(folder: Traversable) -> dict[str, Language]:
    paths = sorted((p for p in folder.iterdir() if p.name.endswith(".toml")), key=lambda p: p.name)
    return {
        code: read_language(code, path.read_text(encoding="utf-8"))
        for path in paths
        if (code := path.name.removesuffix(".toml"))
    }


LANGUAGES = read_languages(files(__name__))


def language(tag: str) -> Language | None:
    """The language of a tag like "ka-GE", if it has a file."""
    return LANGUAGES.get(tag.split("-")[0].lower())


def epub_heading(name: str, tag: str) -> str:
    """One of the EPUB's own headings, in the book's language if it has a file."""
    return (language(tag) or LANGUAGES[FALLBACK]).headings[name]


def all_words(field: str) -> set[str]:
    """A word list from every language, as a book may mix them."""
    return {word for found in LANGUAGES.values() for word in found.words[field]}


def any_of(words: set[str]) -> str:
    """A regular expression for any of the words, longest first."""
    return "|".join(re.escape(word) for word in sorted(words, key=lambda w: (-len(w), w)))
