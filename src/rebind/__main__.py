import sys

from rebind.cli.commands import parse_args
from rebind.pipeline import run


def main() -> int:
    """`rebind` alone opens the window; with a PDF (or --help) it runs on the command line."""
    if len(sys.argv) == 1:
        from rebind.gui import main as gui

        return gui()
    return run(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
