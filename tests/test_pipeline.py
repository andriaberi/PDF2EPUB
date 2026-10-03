from collections.abc import Callable

import pytest

from bookflow.cli.commands import Args
from bookflow.pipeline import run


def test_prints_book_and_lines(
    make_pdf: Callable[..., str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(Args(pdf=make_pdf([["Hello world."]]), language="ka")) == 0
    assert capsys.readouterr().out.splitlines() == [
        "title: None",
        "author: None",
        "language: ka",
        "",
        "Hello world.",
    ]


def test_reports_read_errors(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(Args(pdf="missing.pdf")) == 1
    assert "no such file" in capsys.readouterr().err
