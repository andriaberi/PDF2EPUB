from dataclasses import dataclass
from pathlib import Path

from bookflow.cli.commands import Args

# The choices of the language box, and the code each one passes on.
LANGUAGES = {
    "Detect automatically": None,
    "Georgian": "ka",
    "English": "en",
}


class FormError(Exception):
    """The form can't be converted as filled in."""


@dataclass
class Form:
    """What the window's fields hold, as typed: every field is text."""

    pdf: str = ""
    output: str = ""
    title: str = ""
    author: str = ""
    language: str = "Detect automatically"
    pages: str = ""
    cover: str = ""


def to_args(form: Form) -> Args:
    """The conversion the form asks for. Blank fields are left to Bookflow to work out."""
    pdf = form.pdf.strip()
    if not pdf:
        raise FormError("Choose a PDF book to convert.")
    if not Path(pdf).is_file():
        raise FormError(f"There is no file at {pdf}.")
    return Args(
        pdf=pdf,
        pages=blank_to_none(form.pages),
        title=blank_to_none(form.title),
        author=blank_to_none(form.author),
        language=LANGUAGES.get(form.language),
        output=blank_to_none(form.output),
        cover=blank_to_none(form.cover),
    )


def default_output(pdf: str) -> str:
    """Where the CLI would write the book: next to the PDF."""
    return str(Path(pdf).with_suffix(".epub")) if pdf.strip() else ""


def blank_to_none(text: str) -> str | None:
    return text.strip() or None
