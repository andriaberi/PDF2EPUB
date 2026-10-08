import pytest

from pdf2epub.pdf.language import book_language, detect_language
from pdf2epub.pdf.models import Line, Page


def book(*texts: str) -> list[Page]:
    return [Page(1, 400, 600, [Line(text, 0, 0, 0, 0) for text in texts])]


@pytest.mark.parametrize(
    ("texts", "language"),
    [
        (["1815 წელს შარლ-ფრანსუა-ბიენვენიუ მირიელი ქალაქ დინის"], "ka"),
        (["It was the best of times, it was the worst of times"], "en"),
        (["ბიენვენიუ (Bienvenu) სასურველი, კეთილმოვლენილი."], "ka"),
    ],
)
def test_detects_language(texts: list[str], language: str) -> None:
    assert detect_language(book(*texts)) == language


@pytest.mark.parametrize("text", ["1 2 3", "Он сказал, что это была она"])
def test_unknown(text: str) -> None:
    assert detect_language(book(text)) is None


GEORGIAN = "1815 წელს შარლ-ფრანსუა-ბიენვენიუ მირიელი ქალაქ დინის"
ENGLISH = "It was the best of times, it was the worst of times"


@pytest.mark.parametrize(
    ("declared", "text", "language"),
    [
        ("en-US", GEORGIAN, "ka"),  # a Georgian book made on an English system
        ("ka", ENGLISH, "en"),
        ("ka-GE", GEORGIAN, "ka-GE"),
        ("en-GB", ENGLISH, "en-GB"),
        ("fr", ENGLISH, "fr"),  # Latin script can't tell French from English
        (None, GEORGIAN, "ka"),
        ("ru", "1 2 3", "ru"),
    ],
)
def test_book_language(declared: str | None, text: str, language: str) -> None:
    assert book_language(declared, book(text)) == language
