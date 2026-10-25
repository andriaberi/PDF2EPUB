import sys

import pytest

import pdf2epub.__main__ as entry


def test_a_pdf_runs_on_the_command_line(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["pdf2epub", "missing.pdf"])
    assert entry.main() == 1
    assert "no such file" in capsys.readouterr().err
