import pytest

from bookflow.cli.commands import Args
from bookflow.pipeline import run


def test_run_returns_zero_and_prints_args(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(Args(pdf="book.pdf", language="ka")) == 0
    assert capsys.readouterr().out.splitlines() == [
        "pdf: book.pdf",
        "pages: None",
        "title: None",
        "author: None",
        "language: ka",
    ]
