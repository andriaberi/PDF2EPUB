from dataclasses import dataclass

from pdf2epub.errors import ConvertError


@dataclass
class Cover:
    data: bytes
    width: int
    height: int


class CoverError(ConvertError):
    """The cover image can't be read."""
