from dataclasses import dataclass, field

from pdf2epub.paragraphs import Paragraph


@dataclass
class Heading:
    level: int  # 1 is the outermost division the book uses
    label: str  # "თავი მეორე", "Chapter 2"
    title: str | None = None
    page: int = field(default=0, compare=False)  # where it is printed, 0 if not known
    role: str = "body"

    @property
    def text(self) -> str:
        label = self.label.rstrip(".")
        return f"{label}: {self.title}" if self.title else label


@dataclass
class Note:
    id: str  # unique in the book
    mark: str
    text: str


@dataclass
class Section:
    heading: Heading | None
    paragraphs: list[Paragraph] = field(default_factory=list)
    notes: dict[str, Note] = field(default_factory=dict)
