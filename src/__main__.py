"""Run Bookflow straight from the source tree: `python src book.pdf --flag`."""

from bookflow.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
