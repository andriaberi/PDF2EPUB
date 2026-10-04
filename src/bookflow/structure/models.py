from dataclasses import dataclass, field

from bookflow.paragraphs import Paragraph


@dataclass
class Heading:
    level: int  # 1 is the outermost division the book uses
    label: str  # "თავი მეორე", "Chapter 2"
    title: str | None = None  # "კეთილგონიერება სიბრძნეს აფრთხილებს"

    @property
    def text(self) -> str:
        """ "თავი პირველი: ბატონი მირიელი", or the label alone."""
        label = self.label.rstrip(".")
        return f"{label}: {self.title}" if self.title else label


@dataclass
class Note:
    id: str  # "note-12", the same nowhere else in the book
    mark: str  # "12", as printed in the text: "ფრეილინა[12]"
    text: str


@dataclass
class Section:
    """A heading and the paragraphs up to the next one. Front matter has no heading."""

    heading: Heading | None
    paragraphs: list[Paragraph] = field(default_factory=list)
    notes: dict[str, Note] = field(default_factory=dict)  # the notes its marks refer to
