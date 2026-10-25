"""Convert PDF books into well-structured, reflowable EPUBs."""

from pdf2epub.book import Book, HeadingBlock, TextBlock
from pdf2epub.errors import BookError, ConvertError
from pdf2epub.pdf import render_page
from pdf2epub.pipeline import (
    STEPS,
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
    "render_page",
    "write_book",
]
