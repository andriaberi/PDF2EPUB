from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from bookflow.gui.api import Api, Dialogs, file_size, short_path


class FakeDialogs(Dialogs):
    def __init__(self, open_path: str | None = None, save_path: str | None = None) -> None:
        self.open_path = open_path
        self.save_path = save_path

    def open_file(self, title: str, types: tuple[str, ...]) -> str | None:
        return self.open_path

    def save_file(self, title: str, folder: str, name: str) -> str | None:
        return self.save_path


class Page:
    """Collects what Python sends to the page."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def __call__(self, function: str, data: dict[str, Any]) -> None:
        self.calls.append((function, data))


def test_open_pdf_describes_the_book(make_pdf: Callable[..., str]) -> None:
    pdf = make_pdf([["One."], ["Two."]])
    book = Api(Page(), FakeDialogs()).open_pdf(pdf)
    assert book["pages"] == 2
    assert book["title"] == "book"  # the file name, as the CLI would use
    assert book["saveAs"] == str(Path(pdf).with_suffix(".epub"))


def test_open_pdf_reports_a_bad_file(tmp_path: Path) -> None:
    bad = tmp_path / "bad.pdf"
    bad.write_text("not a pdf")
    assert "can't be opened" in Api(Page(), FakeDialogs()).open_pdf(str(bad))["error"]


def test_chosen_output_sticks_and_gets_its_extension(
    make_pdf: Callable[..., str], tmp_path: Path
) -> None:
    api = Api(Page(), FakeDialogs(save_path=str(tmp_path / "mine")))
    assert api.choose_output() == {
        "path": str(tmp_path / "mine.epub"),
        "label": short_path(str(tmp_path / "mine.epub")),
    }
    assert api.open_pdf(make_pdf([["One."]]))["saveAs"] == str(tmp_path / "mine.epub")


def test_cancelled_dialogs_return_nothing() -> None:
    api = Api(Page(), FakeDialogs())
    assert (api.choose_pdf(), api.choose_output(), api.choose_cover()) == (None, None, None)


def test_convert_reports_progress_then_the_result(
    make_pdf: Callable[..., str], tmp_path: Path
) -> None:
    page = Page()
    api = Api(page, FakeDialogs())
    output = tmp_path / "out.epub"
    assert api.convert({"pdf": make_pdf([["Hello world."]]), "output": str(output)}) is None
    assert api._work_thread is not None
    api._work_thread.join(timeout=30)
    functions = [function for function, _ in page.calls]
    assert functions == ["onProgress"] * 4 + ["onDone"]
    assert [data["index"] for _, data in page.calls[:4]] == [0, 1, 2, 3]
    assert page.calls[-1][1]["name"] == "out.epub"
    assert output.is_file()


def test_convert_reports_errors(make_pdf: Callable[..., str]) -> None:
    page = Page()
    api = Api(page, FakeDialogs())
    assert api.convert({"pdf": make_pdf([["Hello."]]), "pages": "5-9"}) is None
    assert api._work_thread is not None
    api._work_thread.join(timeout=30)
    assert page.calls[-1][0] == "onError"
    assert "past the end" in page.calls[-1][1]["message"]


def test_form_errors_come_back_at_once() -> None:
    assert Api(Page(), FakeDialogs()).convert({"pdf": ""}) == {
        "error": "Choose a PDF book to convert."
    }


@pytest.mark.parametrize(
    ("size", "shown"), [(500, "500 bytes"), (2048, "2.0 KB"), (3 * 1024 * 1024, "3.0 MB")]
)
def test_file_size(tmp_path: Path, size: int, shown: str) -> None:
    file = tmp_path / "f"
    file.write_bytes(b"x" * size)
    assert file_size(str(file)) == shown


def test_short_path() -> None:
    assert short_path(str(Path.home() / "Books" / "a.epub")) == str(Path("~/Books/a.epub"))
    long = "/tmp/" + "x" * 80 + "/ucxo.epub"
    assert len(short_path(long)) == 34
    assert short_path(long).endswith("/ucxo.epub")
