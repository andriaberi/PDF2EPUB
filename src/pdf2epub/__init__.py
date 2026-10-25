"""Convert PDF books into well-structured, reflowable EPUBs."""

from pdf2epub.book import Book, HeadingBlock, TextBlock
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
    "ConvertError",
    "HeadingBlock",
    "Options",
    "Result",
    "TextBlock",
    "convert",
    "read_book",
    "write_book",
]
