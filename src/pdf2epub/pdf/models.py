from dataclasses import dataclass, field

# "i" italic, "b" bold, "bi" both, "" plain
ITALIC, BOLD = "i", "b"


@dataclass
class Line:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    breaks_word: bool = False
    runs: list[tuple[str, str]] = field(default_factory=list)

    @property
    def height(self) -> float:
        return self.y1 - self.y0


@dataclass
class Footnote:
    mark: str  # "12", as in "pneumonia[12]"
    text: str


@dataclass
class Picture:
    data: bytes
    width: int
    height: int
    y0: float
    y1: float


@dataclass
class Page:
    number: int  # 1-based
    width: float
    height: float
    lines: list[Line]
    scanned: bool = False
    footnotes: list[Footnote] = field(default_factory=list)
    pictures: list[Picture] = field(default_factory=list)


@dataclass
class OutlineEntry:
    level: int  # 1 is the outermost
    title: str
    page: int  # 1-based


@dataclass
class Book:
    title: str | None
    author: str | None
    language: str | None
    pages: list[Page]
    outline: list[OutlineEntry] = field(default_factory=list)
