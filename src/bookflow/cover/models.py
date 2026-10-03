from dataclasses import dataclass


@dataclass
class Cover:
    """A cover image, always JPEG so every reader can show it."""

    data: bytes
    width: int
    height: int


class CoverError(Exception):
    """The cover image can't be read."""
