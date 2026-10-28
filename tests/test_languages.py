from pathlib import Path

import pytest

from pdf2epub.languages import (
    LANGUAGES,
    LanguageFileError,
    epub_heading,
    read_language,
    read_languages,
)
from pdf2epub.pdf.language import detect_language
from pdf2epub.pdf.models import Line, Page

FRENCH = """
name = "French"
script = "LATIN"
common = ["le", "la", "et", "les", "des", "est", "il", "une"]
numbers = ["un", "deux", "trois"]
prefaces = ["préface"]
sections = ["prologue", "épilogue"]
contents_titles = ["table des matières"]
notes_titles = ["notes"]
page_abbreviations = ["p"]
credits = ["tradu"]
the_end = ["fin"]
website = []

[divisions]
volume = ["tome"]
part = ["partie"]
book = ["livre"]
chapter = ["chapitre"]

[headings]
contents = "Table des matières"
notes = "Notes"

[romanisation]
"""


def test_reads_every_language_file() -> None:
    assert {"ka", "en"} <= LANGUAGES.keys()
    assert LANGUAGES["ka"].divisions["თავი"] == 4
    assert epub_heading("contents", "ka-GE") == "სარჩევი"
    assert epub_heading("notes", "ru") == "Notes"


def test_a_new_file_is_a_new_language(tmp_path: Path) -> None:
    (tmp_path / "fr.toml").write_text(FRENCH, encoding="utf-8")
    (tmp_path / "README.txt").write_text("not a language", encoding="utf-8")

    found = read_languages(tmp_path)

    assert list(found) == ["fr"]
    assert found["fr"].divisions == {"tome": 1, "partie": 2, "livre": 3, "chapitre": 4}


def test_tells_apart_languages_in_one_script(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(LANGUAGES, "fr", read_language("fr", FRENCH))
    page = Page(1, 400, 600, [Line("Il est la fin et le début des choses", 0, 0, 0, 0)])

    assert detect_language([page]) == "fr"


@pytest.mark.parametrize(
    ("text", "problem"),
    [
        (FRENCH.replace("website = []\n", ""), "missing website"),
        ('colour = "blue"\n' + FRENCH, "unknown colour"),
        (FRENCH + 'colour = "blue"\n', "romanisation"),
        (FRENCH.replace('numbers = ["un"', 'numbers = ["(un"'), "numbers"),
        (FRENCH.replace('chapter = ["chapitre"]\n', ""), "divisions"),
    ],
)
def test_a_wrong_file_says_what_is_wrong(text: str, problem: str) -> None:
    with pytest.raises(LanguageFileError, match=problem):
        read_language("fr", text)
