import pytest

from rebind.cli.commands import Args, parse_args


def test_pdf_only() -> None:
    assert parse_args(["book.pdf"]) == Args(pdf="book.pdf")


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
    assert args == Args(
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
