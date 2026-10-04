import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

from bookflow.cli.commands import Args
from bookflow.cover import Cover
from bookflow.epub import Metadata
from bookflow.paragraphs import Paragraph
from bookflow.pipeline import choose_cover, drop_repeated_title, drop_title_page_reprints, run
from bookflow.structure import Heading, Section


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


def test_front_matter_repeating_the_title_is_dropped() -> None:
    metadata = Metadata(title="Les Misérables", author="Victor Hugo", language="en", identifier="x")
    front = Section(None, [Paragraph("Victor Hugo", 1), Paragraph("LES MISÉRABLES", 1)])
    chapter = Section(Heading(1, "Chapter 1"), [Paragraph("Text.", 2)])
    assert drop_repeated_title([front, chapter], metadata) == [chapter]


def test_front_matter_with_more_is_kept() -> None:
    metadata = Metadata(title="Les Misérables", author=None, language="en", identifier="x")
    front = Section(None, [Paragraph("Les Misérables", 1), Paragraph("A preface.", 1)])
    [kept] = drop_repeated_title([front], metadata)
    assert [p.text for p in kept.paragraphs] == ["A preface."]


def test_title_page_is_dropped_without_the_title_in_metadata() -> None:
    metadata = Metadata(title="ucxo", author=None, language="ka", identifier="x")
    front = Section(None, [Paragraph("ალბერ კამიუ - უცხო", 1)])
    part = Section(Heading(1, "ნაწილი პირველი"))
    assert drop_repeated_title([front, part], metadata) == [part]


def test_title_page_printed_again_before_a_volume_is_dropped() -> None:
    front = Section(None, [Paragraph("ომი და მშვიდობა", 1)])
    chapter = Section(Heading(3, "თავი ოცდამეერთე"), [Paragraph("ტექსტი.", 2)])
    chapter.paragraphs.append(Paragraph("ომი და მშვიდობა", 3))
    volume = Section(Heading(1, "ტომი II"))
    drop_title_page_reprints([front, chapter, volume])
    assert [p.text for p in chapter.paragraphs] == ["ტექსტი."]


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
    assert "cover from --cover" in capsys.readouterr().out
    assert "EPUB/images/cover.jpg" in zipfile.ZipFile(output).namelist()


def test_bad_cover_file_is_reported(
    make_pdf: Callable[..., str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(Args(pdf=make_pdf([["Hello."]]), cover="missing.png")) == 1
    assert "no such cover image" in capsys.readouterr().err
