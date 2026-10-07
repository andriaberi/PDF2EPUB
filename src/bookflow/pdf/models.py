from dataclasses import dataclass, field


@dataclass
class Line:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def height(self) -> float:
        return self.y1 - self.y0


@dataclass
class Page:
    number: int  # 1-based, as printed by --pages
    width: float
    height: float
    lines: list[Line]
    footnotes: list[Line] = field(default_factory=list)
    # A scan with an OCR text layer: its text may hold misreads to clean up.
    scanned: bool = False


@dataclass
class Book:
    title: str | None
    author: str | None
    language: str | None
    pages: list[Page]
