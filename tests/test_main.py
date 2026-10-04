import sys

import pytest

import bookflow.__main__ as entry
import bookflow.gui


def test_no_arguments_opens_the_window(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["bookflow"])
    monkeypatch.setattr(bookflow.gui, "main", lambda: 7)
    assert entry.main() == 7


def test_a_pdf_runs_on_the_command_line(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["bookflow", "missing.pdf"])
    monkeypatch.setattr(bookflow.gui, "main", lambda: pytest.fail("opened the window"))
    assert entry.main() == 1
    assert "no such file" in capsys.readouterr().err
