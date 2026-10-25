from dataclasses import dataclass

from pdf2epub.errors import ConvertError


@dataclass
class Cover:
    """A cover image, always JPEG so every reader can show it."""

    data: bytes
    width: int
    height: int


class CoverError(ConvertError):
    """The cover image can't be read."""
