import importlib.util
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import webview
from webview.dom import DOMEventHandler
from webview.guilib import GUIType

from bookflow import __version__

from .api import Api, Dialogs

PAGE = Path(__file__).parent / "web" / "index.html"

SIZE = (640, 640)
MIN_SIZE = (520, 500)

# Shown behind the page while it loads: the page's own light background.
BACKGROUND = "#f5f5f5"

INSTALL_BACKEND = """\
bookflow: the window needs a web view, and this Python has none.
Install one of these, then run bookflow again:
  pip install "bookflow[qt]"                       (works in any Python)
  sudo apt install python3-gi gir1.2-webkit2-4.1   (Debian, Ubuntu: the system's Python)
Or convert from the command line: bookflow book.pdf"""

NO_DISPLAY = "bookflow: no display to open the window on; use bookflow book.pdf"


class WindowDialogs(Dialogs):
    """File dialogs of the open window."""

    def __init__(self) -> None:
        self.window: webview.Window | None = None

    def open_file(self, title: str, types: tuple[str, ...]) -> str | None:
        return first(self.dialog(webview.FileDialog.OPEN, file_types=(*types, "All files (*.*)")))

    def save_file(self, title: str, folder: str, name: str) -> str | None:
        return first(
            self.dialog(
                webview.FileDialog.SAVE,
                directory=folder,
                save_filename=name,
                file_types=("EPUB books (*.epub)",),
            )
        )

    def dialog(self, kind: webview.FileDialog, **options: Any) -> Sequence[str] | str | None:
        assert self.window is not None
        return self.window.create_file_dialog(kind, **options)


def first(result: Sequence[str] | str | None) -> str | None:
    """Dialogs answer with a path, a list of paths or nothing, depending on the platform."""
    if isinstance(result, str):
        return result or None
    return result[0] if result else None


def backend() -> GUIType | None:
    """The web view to use: the platform's own, or on Linux GTK's if Python has it, else Qt's.

    Raises LookupError when Linux has neither.
    """
    if not sys.platform.startswith("linux"):
        return None
    if importlib.util.find_spec("gi"):
        return "gtk"
    if importlib.util.find_spec("qtpy"):
        return "qt"
    raise LookupError(INSTALL_BACKEND)


def has_display() -> bool:
    if not sys.platform.startswith("linux"):
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def main() -> int:
    if not has_display():
        print(NO_DISPLAY, file=sys.stderr)
        return 1
    try:
        gui = backend()
    except LookupError as e:
        print(e, file=sys.stderr)
        return 1

    dialogs = WindowDialogs()

    def send(function: str, data: dict[str, Any]) -> None:
        if dialogs.window is not None:
            dialogs.window.evaluate_js(f"bookflow.{function}({json.dumps(data)})")

    api = Api(send, dialogs)
    window = webview.create_window(
        f"Bookflow {__version__}",
        url=str(PAGE),
        js_api=api,
        width=SIZE[0],
        height=SIZE[1],
        min_size=MIN_SIZE,
        background_color=BACKGROUND,
    )
    assert window is not None
    dialogs.window = window

    def dropped(event: dict[str, Any]) -> None:
        files = event.get("dataTransfer", {}).get("files", [])
        paths = [file["pywebviewFullPath"] for file in files if file.get("pywebviewFullPath")]
        if paths:
            send("onPicked", api.open_pdf(paths[0]))

    def loaded() -> None:
        # Dropped files reach Python with their full path; the page only sees names.
        # pywebview's documented way; its type hints only allow plain callables.
        handler = DOMEventHandler(dropped, prevent_default=True)
        window.dom.document.events.drop += handler  # type: ignore[arg-type]

    window.events.loaded += loaded
    webview.start(gui=gui)
    return 0
