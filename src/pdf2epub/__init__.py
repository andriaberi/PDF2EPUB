# SPDX-License-Identifier: AGPL-3.0-or-later
"""Convert PDF books into well-structured, reflowable EPUBs."""

from importlib.metadata import PackageNotFoundError, version

from pdf2epub.book import Book, HeadingBlock, PictureBlock, TextBlock
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

try:
    # "1.2026.1028.1": the major version, the year, the month and day, the release that day
    __version__ = version("pdf2epub")
except PackageNotFoundError:  # run from the source folder without installing
    __version__ = "0"

__all__ = [
    "STEPS",
    "Book",
    "BookError",
    "ConvertError",
    "HeadingBlock",
    "Options",
    "PictureBlock",
    "Result",
    "TextBlock",
    "convert",
    "read_book",
    "render_page",
    "write_book",
]
