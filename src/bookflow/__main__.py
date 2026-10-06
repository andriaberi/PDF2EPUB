import sys

from bookflow.cli.commands import parse_args
from bookflow.pipeline import run


def main() -> int:
    """`bookflow` alone opens the window; with a PDF (or --help) it runs on the command line."""
    if len(sys.argv) == 1:
        from bookflow.gui import main as gui

        return gui()
    return run(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
