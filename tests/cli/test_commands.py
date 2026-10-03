import sys

import pytest

from bookflow.cli.commands import Args, extract_args


def parse(monkeypatch: pytest.MonkeyPatch, *argv: str) -> Args:
    monkeypatch.setattr(sys, "argv", ["bookflow", *argv])
    return extract_args()


def test_pdf_only(monkeypatch: pytest.MonkeyPatch) -> None:
    assert parse(monkeypatch, "book.pdf") == Args(pdf="book.pdf")


def test_all_options(monkeypatch: pytest.MonkeyPatch) -> None:
    args = parse(
        monkeypatch,
        "book.pdf",
        "--pages",
        "1-20",
        "--title",
        "Title",
        "--author",
        "Author",
        "--language",
        "ka",
        "--output",
        "out.epub",
        "--cover",
        "cover.jpg",
    )
    assert args == Args(
        pdf="book.pdf",
        pages="1-20",
        title="Title",
        author="Author",
        language="ka",
        output="out.epub",
        cover="cover.jpg",
    )


def test_missing_pdf_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(SystemExit) as exc:
        parse(monkeypatch)
    assert exc.value.code == 2
