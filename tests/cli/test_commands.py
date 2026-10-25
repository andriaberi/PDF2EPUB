import pytest

from pdf2epub.cli.commands import parse_args
from pdf2epub.pipeline import Options


def test_pdf_only() -> None:
    assert parse_args(["book.pdf"]) == Options(pdf="book.pdf")


def test_all_options() -> None:
    args = parse_args(
        [
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
        ]
    )
    assert args == Options(
        pdf="book.pdf",
        pages="1-20",
        title="Title",
        author="Author",
        language="ka",
        output="out.epub",
        cover="cover.jpg",
    )


def test_missing_pdf_exits() -> None:
    with pytest.raises(SystemExit) as exc:
        parse_args([])
    assert exc.value.code == 2
