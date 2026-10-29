from dataclasses import dataclass, field


@dataclass
class Line:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    # Ends partway through a word that the next line finishes, with no hyphen to show it.
    breaks_word: bool = False

    @property
    def height(self) -> float:
        return self.y1 - self.y0


@dataclass
class Footnote:
    mark: str  # "12", as its mark reads in the text: "pneumonia[12]"
    text: str


@dataclass
class Page:
    number: int  # 1-based
    width: float
    height: float
    lines: list[Line]
    # A scan with an OCR text layer: its text may hold misreads to clean up.
    scanned: bool = False
    # The notes at its foot whose marks in its text could be told: raised digits.
    footnotes: list[Footnote] = field(default_factory=list)


@dataclass
class OutlineEntry:
    """A bookmark in the PDF's outline: a heading as the PDF's maker listed it."""

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
