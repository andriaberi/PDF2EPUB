import sys

from pdf2epub.cli.commands import parse_args
from pdf2epub.pipeline import run


def main() -> int:
    """`pdf2epub` alone opens the window; with a PDF (or --help) it runs on the command line."""
    if len(sys.argv) == 1:
        from pdf2epub.gui import main as gui

        return gui()
    return run(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
