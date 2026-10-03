from dataclasses import dataclass, field

from bookflow.paragraphs import Paragraph


@dataclass
class Heading:
    level: int  # 1 is the outermost division the book uses
    label: str  # "თავი მეორე", "Chapter 2"
    title: str | None = None  # "კეთილგონიერება სიბრძნეს აფრთხილებს"

    @property
    def text(self) -> str:
        return f"{self.label}. {self.title}" if self.title else self.label


@dataclass
class Section:
    """A heading and the paragraphs up to the next one. Front matter has no heading."""

    heading: Heading | None
    paragraphs: list[Paragraph] = field(default_factory=list)
