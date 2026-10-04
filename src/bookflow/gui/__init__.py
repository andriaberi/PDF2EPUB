import sys

INSTALL_TK = (
    "bookflow-gui needs Tk, which this Python doesn't have.\n"
    "On Debian or Ubuntu: sudo apt install python3-tk\n"
    "On Fedora: sudo dnf install python3-tkinter\n"
    "On Windows and macOS, the python.org installers include it."
)


def main() -> int:
    """Open the window; without Tk, say how to get it instead of failing with a traceback."""
    try:
        from .app import main as run_app
    except ModuleNotFoundError as e:
        if e.name not in ("tkinter", "_tkinter"):
            raise
        print(INSTALL_TK, file=sys.stderr)
        return 1
    return run_app()
