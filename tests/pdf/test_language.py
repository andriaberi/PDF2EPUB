import pytest

from rebind.pdf.language import detect_language
from rebind.pdf.models import Line, Page


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
