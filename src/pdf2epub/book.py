import base64
from dataclasses import asdict, dataclass, field
from typing import Any

from pdf2epub.cover import Cover
from pdf2epub.epub import Metadata
from pdf2epub.paragraphs import Paragraph
from pdf2epub.pdf import Line
from pdf2epub.pdf.text import NOTE_MARK
from pdf2epub.structure import Heading, Note, Section

# Goes up whenever the shape of to_dict()'s data changes, so older data is refused.
VERSION = 1


class BookError(Exception):
    """The book's data can't be read: another version, or a part missing or mistyped."""


@dataclass(kw_only=True)
class Block:
    id: str  # the same however the blocks around it change
    page: int  # the PDF page it is printed on, from 1; 0 if not known
    role: str = "body"
    include: bool = True  # whether the EPUB shows it


@dataclass(kw_only=True)
class HeadingBlock(Block):
    level: int  # 1 is the outermost division the book uses
    label: str  # "თავი მეორე", "Chapter 2"
    title: str | None = None


@dataclass(kw_only=True)
class TextBlock(Block):
    text: str
    lines: list[str] = field(default_factory=list)  # a verse paragraph's lines, as printed
    verse: bool = False
    epigraph: bool = False  # a quotation set under a heading
    attribution: bool = False  # the line naming whose the epigraph is
    notes: dict[str, str] = field(default_factory=dict)  # each mark's note id: "12" -> "note-12"


@dataclass
class Book:
    """The book between reading and writing: its blocks in reading order, a heading
    starting each section, so it is easy to show and edit."""

    metadata: Metadata
    blocks: list[HeadingBlock | TextBlock]
    notes: list[Note]
    cover: Cover | None
    cover_source: str  # "cover from the PDF", "cover from the given image" or "no cover"

    @classmethod
    def from_sections(
        cls,
        metadata: Metadata,
        sections: list[Section],
        notes: list[Note],
        cover: Cover | None,
        cover_source: str,
    ) -> "Book":
        blocks: list[HeadingBlock | TextBlock] = []
        for section in sections:
            if section.heading:
                heading = section.heading
                blocks.append(
                    HeadingBlock(
                        id=f"b{len(blocks) + 1}",
                        page=heading.page,
                        level=heading.level,
                        label=heading.label,
                        title=heading.title,
                    )
                )
            for paragraph in section.paragraphs:
                lines = [line.text for line in paragraph.lines] if paragraph.verse else []
                marks = [*NOTE_MARK.findall(paragraph.text), *NOTE_MARK.findall(" ".join(lines))]
                blocks.append(
                    TextBlock(
                        id=f"b{len(blocks) + 1}",
                        page=paragraph.page,
                        text=paragraph.text,
                        lines=lines,
                        verse=paragraph.verse,
                        epigraph=paragraph.epigraph,
                        attribution=paragraph.attribution,
                        notes={m: section.notes[m].id for m in marks if m in section.notes},
                    )
                )
        return cls(metadata, blocks, notes, cover, cover_source)

    def sections(self) -> list[Section]:
        """The included blocks as sections, each heading starting one."""
        notes = {note.id: note for note in self.notes}
        sections: list[Section] = []
        for block in self.blocks:
            if not block.include:
                continue
            if isinstance(block, HeadingBlock):
                heading = Heading(block.level, block.label, block.title, page=block.page)
                sections.append(Section(heading))
                continue
            if not sections:
                sections.append(Section(heading=None))
            section = sections[-1]
            section.paragraphs.append(
                Paragraph(
                    block.text,
                    block.page,
                    # Verse is written line by line; where the lines were no longer matters.
                    [Line(text, 0, 0, 0, 0) for text in block.lines],
                    verse=block.verse,
                    epigraph=block.epigraph,
                    attribution=block.attribution,
                )
            )
            for mark, note_id in block.notes.items():
                if note_id in notes:
                    section.notes.setdefault(mark, notes[note_id])
        return sections

    def to_dict(self) -> dict[str, Any]:
        """The book as JSON-able data; from_dict() reads it back."""
        cover = None
        if self.cover:
            data = base64.b64encode(self.cover.data).decode()
            cover = {"data": data, "width": self.cover.width, "height": self.cover.height}
        return {
            "version": VERSION,
            "metadata": asdict(self.metadata),
            "blocks": [
                {"type": "heading" if isinstance(block, HeadingBlock) else "text", **asdict(block)}
                for block in self.blocks
            ],
            "notes": [asdict(note) for note in self.notes],
            "cover": cover,
            "cover_source": self.cover_source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Book":
        if data.get("version") != VERSION:
            raise BookError(f"book data of version {data.get('version')}, not {VERSION}")
        try:
            cover = None
            if data["cover"]:
                image = data["cover"]
                cover = Cover(base64.b64decode(image["data"]), image["width"], image["height"])
            return cls(
                Metadata(**data["metadata"]),
                [read_block(block) for block in data["blocks"]],
                [Note(**note) for note in data["notes"]],
                cover,
                data["cover_source"],
            )
        except (KeyError, TypeError, ValueError) as e:
            raise BookError(f"bad book data: {e!r}") from None


def read_block(data: dict[str, Any]) -> HeadingBlock | TextBlock:
    fields = {key: value for key, value in data.items() if key != "type"}
    if data.get("type") == "heading":
        return HeadingBlock(**fields)
    if data.get("type") == "text":
        return TextBlock(**fields)
    raise BookError(f"unknown block type {data.get('type')!r}")
