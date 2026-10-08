import os
import subprocess
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pdf2epub.cli.commands import Args
from pdf2epub.pipeline import ConvertError, Result, convert

from .form import Form, FormError, default_output, describe_pdf, to_args

# The steps convert() reports, in order, so the page can show how far along it is.
STEPS = ["Reading the PDF", "Finding paragraphs", "Finding chapters", "Writing the EPUB"]

# Calls a JavaScript function on the page by name with JSON-able arguments.
Send = Callable[[str, dict[str, Any]], None]


class Api:
    """What the page can ask of Python. Every method returns plain JSON-able data.

    The page sees only the public methods; pywebview hides names starting with "_".
    File dialogs come from `dialogs`, so the Api works without a window in tests.
    """

    def __init__(self, send: Send, dialogs: "Dialogs") -> None:
        self._send = send
        self._dialogs = dialogs
        self._output_chosen = False
        self._save_as = ""
        self._converting = False
        self._work_thread: threading.Thread | None = None

    def choose_pdf(self) -> dict[str, Any] | None:
        path = self._dialogs.open_file("Choose a PDF book", ("PDF books (*.pdf)",))
        return self.open_pdf(path) if path else None

    def open_pdf(self, path: str) -> dict[str, Any]:
        """Everything the page shows about a PDF, or an error to show instead."""
        info = describe_pdf(path)
        if info is None:
            return {"error": f"{Path(path).name} can't be opened as a PDF."}
        if not self._output_chosen:
            self._save_as = default_output(path)
        return {
            "path": path,
            "name": Path(path).name,
            "pages": info.pages,
            "size": file_size(path),
            "title": info.title or Path(path).stem,
            "author": info.author or "",
            "saveAs": self._save_as,
            "saveAsLabel": short_path(self._save_as),
        }

    def choose_output(self) -> dict[str, str] | None:
        current = Path(self._save_as or "book.epub")
        path = self._dialogs.save_file("Save the EPUB as", str(current.parent), current.name)
        if not path:
            return None
        if not path.lower().endswith(".epub"):
            path += ".epub"
        self._output_chosen = True
        self._save_as = path
        return {"path": path, "label": short_path(path)}

    def choose_cover(self) -> dict[str, str] | None:
        path = self._dialogs.open_file(
            "Choose a cover image", ("Images (*.jpg;*.jpeg;*.png;*.webp;*.gif;*.bmp)",)
        )
        return {"path": path, "name": Path(path).name} if path else None

    def convert(self, fields: dict[str, str]) -> dict[str, str] | None:
        """Start converting in the background; progress and the end come through `send`.

        Returns an error at once when the form can't be converted as filled in.
        """
        if self._converting:
            return {"error": "A book is already being converted."}
        form = Form(**{key: str(fields.get(key, "")) for key in Form.__dataclass_fields__})
        form.output = form.output or self._save_as
        try:
            args = to_args(form)
        except FormError as e:
            return {"error": str(e)}
        self._converting = True
        self._work_thread = threading.Thread(target=self._work, args=(args,), daemon=True)
        self._work_thread.start()
        return None

    def _work(self, args: Args) -> None:
        def progress(step: str) -> None:
            index = STEPS.index(step) if step in STEPS else 0
            self._send("onProgress", {"step": step, "index": index, "count": len(STEPS)})

        try:
            result = convert(args, progress)
        except ConvertError as e:
            self._send("onError", {"message": str(e)})
        except Exception as e:  # a bug: say so rather than leave the page waiting
            self._send("onError", {"message": f"Something went wrong: {e!r}"})
        else:
            self._send("onDone", result_data(result))
        finally:
            self._converting = False

    def show_in_folder(self, path: str) -> None:
        show_in_folder(Path(path))


class Dialogs:
    """Native file dialogs; the window supplies the real ones."""

    def open_file(self, title: str, types: tuple[str, ...]) -> str | None:
        raise NotImplementedError

    def save_file(self, title: str, folder: str, name: str) -> str | None:
        raise NotImplementedError


def result_data(result: Result) -> dict[str, Any]:
    return {
        "output": str(result.output),
        "name": result.output.name,
        "headings": result.headings,
        "paragraphs": result.paragraphs,
        "notes": result.notes,
        "cover": result.cover,
        "size": file_size(str(result.output)),
    }


def short_path(path: str, limit: int = 34) -> str:
    """A path that fits a small space: the home folder as ~, the middle cut out if long."""
    home = str(Path.home())
    if path.startswith(home + os.sep):
        path = "~" + path[len(home) :]
    if len(path) <= limit:
        return path
    head = limit // 3
    return f"{path[:head]}…{path[-(limit - head - 1) :]}"


def file_size(path: str) -> str:
    try:
        size = float(Path(path).stat().st_size)
    except OSError:
        return ""
    if size < 1024:
        return f"{size:.0f} bytes"
    size /= 1024
    return f"{size:.1f} KB" if size < 1024 else f"{size / 1024:.1f} MB"


def show_in_folder(path: Path) -> None:
    """Open the file manager at the folder holding the file."""
    folder = path.parent
    if sys.platform == "win32":
        os.startfile(folder)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(folder)])
