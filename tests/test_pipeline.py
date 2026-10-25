import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

from pdf2epub.cover import Cover
from pdf2epub.pipeline import (
    STEPS,
    ConvertError,
    Options,
    choose_cover,
    convert,
)


def test_writes_an_epub(make_pdf: Callable[..., str], tmp_path: Path) -> None:
    output = tmp_path / "out.epub"
    convert(Options(pdf=make_pdf([["Hello world."]]), output=str(output)))
    assert zipfile.ZipFile(output).read("mimetype") == b"application/epub+zip"


def test_convert_reports_each_step(make_pdf: Callable[..., str], tmp_path: Path) -> None:
    steps: list[str] = []
    result = convert(
        Options(pdf=make_pdf([["Hello world."]]), output=str(tmp_path / "out.epub")), steps.append
    )
    assert tuple(steps) == STEPS
    assert result.output == tmp_path / "out.epub"
    assert (result.headings, result.paragraphs, result.notes) == (0, 1, 0)


def test_convert_raises_instead_of_printing(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(ConvertError, match="no such file"):
        convert(Options(pdf="missing.pdf", output="out.epub"))
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


def test_given_cover_is_used_without_a_cover_in_the_pdf(
    make_pdf: Callable[..., str], tmp_path: Path
) -> None:
    import pymupdf

    image = tmp_path / "cover.png"
    pymupdf.open().new_page().get_pixmap().save(image)
    output = tmp_path / "out.epub"
    result = convert(Options(pdf=make_pdf([["Hello."]]), output=str(output), cover=str(image)))
    assert result.cover == "cover from the given image"
    assert "EPUB/images/cover.jpg" in zipfile.ZipFile(output).namelist()


def test_bad_cover_file_is_reported(make_pdf: Callable[..., str], tmp_path: Path) -> None:
    output = str(tmp_path / "out.epub")
    with pytest.raises(ConvertError, match="no such cover image"):
        convert(Options(pdf=make_pdf([["Hello."]]), output=output, cover="missing.png"))
