from collections.abc import Callable
from pathlib import Path

import pytest

from rebind.gui.form import Form, FormError, default_output, describe_pdf, to_args


def test_blank_fields_are_left_to_rebind(tmp_path: Path) -> None:
    pdf = tmp_path / "book.pdf"
    pdf.write_bytes(b"%PDF")
    args = to_args(Form(pdf=f" {pdf} ", title="  ", pages=""))
    assert args.pdf == str(pdf)
    assert (args.title, args.author, args.pages, args.output, args.cover) == (None,) * 5
    assert args.language is None


def test_fields_are_passed_on(tmp_path: Path) -> None:
    pdf = tmp_path / "book.pdf"
    pdf.write_bytes(b"%PDF")
    form = Form(pdf=str(pdf), title="უცხო", language="Georgian", pages="1-20", output="out.epub")
    args = to_args(form)
    assert (args.title, args.language, args.pages, args.output) == (
        "უცხო",
        "ka",
        "1-20",
        "out.epub",
    )


def test_a_pdf_is_needed() -> None:
    with pytest.raises(FormError, match="Choose a PDF"):
        to_args(Form())


def test_the_pdf_must_exist(tmp_path: Path) -> None:
    with pytest.raises(FormError, match="no file"):
        to_args(Form(pdf=str(tmp_path / "missing.pdf")))


def test_output_defaults_to_next_to_the_pdf() -> None:
    assert default_output("/books/ucxo.pdf") == str(Path("/books/ucxo.epub"))
    assert default_output("  ") == ""


def test_describe_pdf(make_pdf: Callable[..., str], tmp_path: Path) -> None:
    info = describe_pdf(make_pdf([["One."], ["Two."]]))
    assert info is not None
    assert info.pages == 2
    bad = tmp_path / "bad.pdf"
    bad.write_text("not a pdf")
    assert describe_pdf(str(bad)) is None
