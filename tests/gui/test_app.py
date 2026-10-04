from collections.abc import Iterator
from pathlib import Path

import pytest

tk = pytest.importorskip("tkinter")

from bookflow.gui.app import App  # noqa: E402


@pytest.fixture
def app() -> Iterator[App]:
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    root.withdraw()
    yield App(root)
    root.destroy()


def test_output_follows_the_pdf_until_chosen(app: App) -> None:
    app.pdf.set("/books/ucxo.pdf")
    assert app.save_as.get() == str(Path("/books/ucxo.epub"))
    app.output_chosen = True
    app.pdf.set("/books/other.pdf")
    assert app.save_as.get() == str(Path("/books/ucxo.epub"))


def test_form_reads_the_fields(app: App) -> None:
    app.book_title.set("უცხო")
    app.language.set("English")
    form = app.form()
    assert (form.title, form.language) == ("უცხო", "English")
