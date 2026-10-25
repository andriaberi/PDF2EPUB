import argparse
from collections.abc import Sequence

from pdf2epub.pipeline import Options


def parse_args(argv: Sequence[str] | None = None) -> Options:
    """The command line's options; `argv` defaults to the program's own arguments."""
    parser = argparse.ArgumentParser(
        prog="pdf2epub",
        description="Convert a PDF book into a reflowable EPUB.",
    )
    parser.add_argument("pdf", help="the PDF book to convert")
    parser.add_argument(
        "-o", "--output", metavar="PATH", help="where to write the EPUB (default: next to the PDF)"
    )
    parser.add_argument(
        "--pages", metavar="SPEC", help="convert only these pages, 1-based: 1-3,7,10-12"
    )
    parser.add_argument("--title", metavar="TEXT", help="the book's title (default: from the PDF)")
    parser.add_argument(
        "--author", metavar="TEXT", help="the book's author (default: from the PDF)"
    )
    parser.add_argument(
        "--language",
        metavar="CODE",
        help="the book's language, such as ka or en (default: detected)",
    )
    parser.add_argument(
        "--cover",
        metavar="IMAGE",
        help="a cover image, used only when the PDF has no cover of its own",
    )

    return Options(**vars(parser.parse_args(argv)))
