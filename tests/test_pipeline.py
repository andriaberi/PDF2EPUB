import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

from rebind.cli.commands import Args
from rebind.cover import Cover
from rebind.pipeline import (
    ConvertError,
    choose_cover,
    convert,
    run,
)


def test_writes_an_epub(
    make_pdf: Callable[..., str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "out.epub"
    assert run(Args(pdf=make_pdf([["Hello world."]]), output=str(output))) == 0
    assert "Wrote" in capsys.readouterr().out
    assert zipfile.ZipFile(output).read("mimetype") == b"application/epub+zip"


def test_writes_next_to_the_pdf_by_default(make_pdf: Callable[..., str]) -> None:
    pdf = Path(make_pdf([["Hello world."]]))
    assert run(Args(pdf=str(pdf))) == 0
    assert pdf.with_suffix(".epub").is_file()


def test_reports_read_errors(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(Args(pdf="missing.pdf")) == 1
    assert "no such file" in capsys.readouterr().err


def test_convert_reports_each_step(make_pdf: Callable[..., str], tmp_path: Path) -> None:
    steps: list[str] = []
    result = convert(
        Args(pdf=make_pdf([["Hello world."]]), output=str(tmp_path / "out.epub")), steps.append
    )
    assert steps == [
        "Reading the PDF",
        "Finding paragraphs",
        "Finding chapters",
        "Writing the EPUB",
    ]
    assert result.output == tmp_path / "out.epub"
    assert result.summary().startswith(f"Wrote {tmp_path / 'out.epub'}: 0 headings, 1 paragraphs")


def test_convert_raises_instead_of_printing(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(ConvertError, match="no such file"):
        convert(Args(pdf="missing.pdf"))
    assert capsys.readouterr() == ("", "")


OWN = Cover(b"own", 1, 1)
GIVEN = Cover(b"given", 1, 1)


@pytest.mark.parametrize(
    ("own", "given", "chosen"),
    [(OWN, GIVEN, OWN), (OWN, None, OWN), (None, GIVEN, GIVEN), (None, None, None)],
)
def test_the_books_own_cover_comes_first(
    own: Cover | None, given: Cover | None, chosen: Cover | None
) -> None:
    assert choose_cover(own, given)[0] is chosen


def test_cover_flag_is_used_without_a_cover_in_the_pdf(
    make_pdf: Callable[..., str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import pymupdf

    image = tmp_path / "cover.png"
    pymupdf.open().new_page().get_pixmap().save(image)
    output = tmp_path / "out.epub"
    assert run(Args(pdf=make_pdf([["Hello."]]), cover=str(image), output=str(output))) == 0
    assert "cover from the given image" in capsys.readouterr().out
    assert "EPUB/images/cover.jpg" in zipfile.ZipFile(output).namelist()


def test_bad_cover_file_is_reported(
    make_pdf: Callable[..., str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(Args(pdf=make_pdf([["Hello."]]), cover="missing.png")) == 1
    assert "no such cover image" in capsys.readouterr().err
