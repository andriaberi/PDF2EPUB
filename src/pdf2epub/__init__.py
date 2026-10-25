"""Convert PDF books into well-structured, reflowable EPUBs."""

from pdf2epub.book import Book, BookError, HeadingBlock, TextBlock
from pdf2epub.pipeline import (
    STEPS,
    ConvertError,
    Options,
    Result,
    convert,
    read_book,
    write_book,
)

__all__ = [
    "STEPS",
    "Book",
    "BookError",
    "ConvertError",
    "HeadingBlock",
    "Options",
    "Result",
    "TextBlock",
    "convert",
    "read_book",
    "write_book",
]
