"""Convert a book by hand to see how it comes out: python scripts/try_book.py book.pdf"""

import argparse
import time
from pathlib import Path

from pdf2epub.pipeline import ConvertError, Options, convert


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert a PDF book into an EPUB.")
    parser.add_argument("pdf")
    parser.add_argument("-o", "--output", help="default: next to the PDF")
    parser.add_argument("--pages", help="such as 1-3,7,10-12")
    parser.add_argument("--cover", help="used when the PDF has no cover of its own")
    args = parser.parse_args()

    output = args.output or str(Path(args.pdf).with_suffix(".epub"))
    start = time.perf_counter()
    try:
        result = convert(Options(args.pdf, output, pages=args.pages, cover=args.cover))
    except ConvertError as e:
        print(f"error: {e}")
        return 1
    found = f"{result.headings} headings, {result.paragraphs} paragraphs, {result.notes} notes"
    print(f"Wrote {result.output}: {found}, {result.cover} ({time.perf_counter() - start:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
