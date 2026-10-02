import argparse
from dataclasses import dataclass


@dataclass
class Args:
    pdf: str
    pages: str | None = None
    title: str | None = None
    author: str | None = None
    language: str | None = None


def extract_args() -> Args:
    parser = argparse.ArgumentParser(prog="bookflow", description="Convert PDF books to EPUB.")

    parser.add_argument("pdf", help="Path to the PDF file")
    parser.add_argument("--pages", help="Pages to extract from the PDF")
    parser.add_argument("--title", help="Title of the book")
    parser.add_argument("--author", help="Author of the book")
    parser.add_argument("--language", help="Language of the book")

    args = parser.parse_args()

    return Args(
        pdf=args.pdf, pages=args.pages, title=args.title, author=args.author, language=args.language
    )
