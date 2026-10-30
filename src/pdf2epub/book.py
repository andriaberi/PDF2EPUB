import base64
import re
from collections.abc import Collection
from dataclasses import asdict, dataclass, field
from typing import Any

from pdf2epub.cover import Cover, load_cover
from pdf2epub.epub import Metadata
from pdf2epub.errors import BookError
from pdf2epub.paragraphs import Paragraph
from pdf2epub.pdf import Line, Picture
from pdf2epub.pdf.text import NOTE_MARK
from pdf2epub.structure import Heading, Note, Section
from pdf2epub.styles import styled_text

ROLES = ("body", "contents", "preface", "front", "title-page", "reprint", "back")

# Heading levels run from the outermost division to a subheading set in the text.
MAX_LEVEL = 6

# A JPEG starts with these bytes; the EPUB names its cover and pictures .jpg.
JPEG_START = b"\xff\xd8"

# Where the cover came from.
PDF_COVER = "cover from the PDF"
GIVEN_COVER = "cover from the given image"
NO_COVER = "no cover"

# Goes up whenever the shape of to_dict()'s data changes, so older data is refused.
VERSION = 1


@dataclass(kw_only=True)
class Block:
    id: str  # the same however the blocks around it change
    page: int  # the PDF page it is printed on, from 1; 0 if not known
    role: str = "body"  # see Paragraph.role
    include: bool = True  # whether the EPUB shows it; at first, only the body is shown


@dataclass(kw_only=True)
class HeadingBlock(Block):
    level: int  # 1 is the outermost division the book uses
    label: str  # "თავი მეორე", "Chapter 2"
    title: str | None = None


@dataclass(kw_only=True)
class TextBlock(Block):
    text: str  # its italics and bold in tags: "a <i>very</i> good day"
    lines: list[str] = field(default_factory=list)  # a verse paragraph's lines, as printed
    verse: bool = False
    epigraph: bool = False  # a quotation set under a heading
    attribution: bool = False  # the line naming whose the epigraph is
    notes: dict[str, str] = field(default_factory=dict)  # each mark's note id: {"12": "note-12"}


@dataclass(kw_only=True)
class PictureBlock(Block):
    data: bytes  # a JPEG
    width: int  # in pixels
    height: int


@dataclass
class Book:
    """The book between reading and writing: its blocks in reading order, a heading
    starting each section, so it is easy to show and edit."""

    metadata: Metadata
    blocks: list[HeadingBlock | TextBlock | PictureBlock]
    notes: list[Note]
    cover: Cover | None
    cover_source: str  # PDF_COVER, GIVEN_COVER or NO_COVER
    include_notes: bool = True  # False leaves out the notes and their marks in the text

    @classmethod
    def from_sections(
        cls,
        metadata: Metadata,
        sections: list[Section],
        notes: list[Note],
        cover: Cover | None,
        cover_source: str,
    ) -> "Book":
        blocks: list[HeadingBlock | TextBlock | PictureBlock] = []
        for section in sections:
            if section.heading:
                heading = section.heading
                blocks.append(
                    HeadingBlock(
                        id=f"b{len(blocks) + 1}",
                        page=heading.page,
                        role=heading.role,
                        include=heading.role == "body",
                        level=heading.level,
                        label=heading.label,
                        title=heading.title,
                    )
                )
            for paragraph in section.paragraphs:
                if picture := paragraph.picture:
                    blocks.append(
                        PictureBlock(
                            id=f"b{len(blocks) + 1}",
                            page=paragraph.page,
                            role=paragraph.role,
                            include=paragraph.role == "body",
                            data=picture.data,
                            width=picture.width,
                            height=picture.height,
                        )
                    )
                    continue
                lines = [line.text for line in paragraph.lines] if paragraph.verse else []
                marks = [*NOTE_MARK.findall(paragraph.text), *NOTE_MARK.findall(" ".join(lines))]
                # A scene break stays as printed, to be told as one.
                text = paragraph.text
                if not paragraph.scene_break:
                    text = styled_text(text, paragraph.lines)
                    if paragraph.verse:
                        lines = [styled_text(line.text, [line]) for line in paragraph.lines]
                blocks.append(
                    TextBlock(
                        id=f"b{len(blocks) + 1}",
                        page=paragraph.page,
                        role=paragraph.role,
                        include=paragraph.role == "body",
                        text=text,
                        lines=lines,
                        verse=paragraph.verse,
                        epigraph=paragraph.epigraph,
                        attribution=paragraph.attribution,
                        notes={m: section.notes[m].id for m in marks if m in section.notes},
                    )
                )
        return cls(metadata, blocks, notes, cover, cover_source)

    def sections(self) -> list[Section]:
        """The included blocks as sections, each heading starting one. A mark whose note
        is left out, or no longer in the book, is taken out of the text."""
        notes = {note.id: note for note in self.written_notes()}
        sections: list[Section] = []
        for block in self.blocks:
            if not block.include:
                continue
            if isinstance(block, HeadingBlock):
                heading = Heading(
                    block.level, block.label, block.title, page=block.page, role=block.role
                )
                sections.append(Section(heading))
                continue
            if not sections:
                sections.append(Section(heading=None))
            section = sections[-1]
            if isinstance(block, PictureBlock):
                picture = Picture(block.data, block.width, block.height, 0, 0)
                section.paragraphs.append(
                    Paragraph("", block.page, picture=picture, role=block.role)
                )
                continue
            links = {mark: notes[i] for mark, i in block.notes.items() if i in notes}
            unwritten = block.notes.keys() - links.keys()
            section.paragraphs.append(
                Paragraph(
                    without_marks(block.text, unwritten),
                    block.page,
                    # Verse is written line by line; where the lines were no longer matters.
                    [Line(without_marks(text, unwritten), 0, 0, 0, 0) for text in block.lines],
                    verse=block.verse,
                    epigraph=block.epigraph,
                    attribution=block.attribution,
                    role=block.role,
                )
            )
            for mark, note in links.items():
                section.notes.setdefault(mark, note)
        return sections

    def set_cover(self, image: str | bytes) -> None:
        """Use this image, a path or its bytes, as the cover; CoverError if it isn't one."""
        self.cover = load_cover(image)
        self.cover_source = GIVEN_COVER

    def problems(self) -> list[str]:
        """What keeps the book, as edited, from being written; empty if nothing does."""
        found: list[str] = []
        metadata = self.metadata
        for name in ("title", "language", "identifier"):
            if not is_text(getattr(metadata, name)):
                found.append(f"the book needs a {name}")
        if not is_text_or_none(metadata.author):
            found.append("the author must be text")

        ids: set[str] = set()
        for block in self.blocks:
            found.extend(block_problems(block, ids))
            ids.add(block.id)
        if not any(block.include is True for block in self.blocks):
            found.append("no block is included, so there is nothing to write")

        note_ids: set[str] = set()
        for note in self.notes:
            if not is_text(note.id) or note.id in note_ids:
                found.append(f"note {note.id!r}: each note needs an id of its own")
            note_ids.add(note.id)
            if not isinstance(note.mark, str) or not note.mark.isdigit():
                found.append(f"note {note.id!r}: its mark must be a number")
            if not is_text(note.text):
                found.append(f"note {note.id!r} has no text")
        if not is_flag(self.include_notes):
            found.append("include_notes must be true or false")

        cover = self.cover
        if cover and not is_jpeg(cover.data, cover.width, cover.height):
            found.append("the cover must be a JPEG image with its width and height")
        return found

    def written_notes(self) -> list[Note]:
        return self.notes if self.include_notes else []

    def to_dict(self) -> dict[str, Any]:
        """The book as JSON-able data; from_dict() reads it back."""
        cover = None
        if self.cover:
            data = base64.b64encode(self.cover.data).decode()
            cover = {"data": data, "width": self.cover.width, "height": self.cover.height}
        return {
            "version": VERSION,
            "metadata": asdict(self.metadata),
            "blocks": [block_data(block) for block in self.blocks],
            "notes": [asdict(note) for note in self.notes],
            "cover": cover,
            "cover_source": self.cover_source,
            "include_notes": self.include_notes,
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
                data["include_notes"],
            )
        except (KeyError, TypeError, ValueError) as e:
            raise BookError(f"bad book data: {e!r}") from None


def block_data(block: HeadingBlock | TextBlock | PictureBlock) -> dict[str, Any]:
    if isinstance(block, PictureBlock):
        return {"type": "picture", **asdict(block), "data": base64.b64encode(block.data).decode()}
    return {"type": "heading" if isinstance(block, HeadingBlock) else "text", **asdict(block)}


def read_block(data: dict[str, Any]) -> HeadingBlock | TextBlock | PictureBlock:
    fields = {key: value for key, value in data.items() if key != "type"}
    if data.get("type") == "heading":
        return HeadingBlock(**fields)
    if data.get("type") == "text":
        return TextBlock(**fields)
    if data.get("type") == "picture":
        return PictureBlock(**{**fields, "data": base64.b64decode(fields["data"])})
    raise BookError(f"unknown block type {data.get('type')!r}")


def block_problems(block: HeadingBlock | TextBlock | PictureBlock, ids: set[str]) -> list[str]:
    where = f"block {block.id!r}"
    found = []
    if not is_text(block.id) or block.id in ids:
        found.append(f"{where}: each block needs an id of its own")
    if type(block.page) is not int or block.page < 0:
        found.append(f"{where}: its page must be a whole number, 0 if not known")
    if block.role not in ROLES:
        found.append(f"{where}: unknown role {block.role!r}")
    if not is_flag(block.include):
        found.append(f"{where}: include must be true or false")

    if isinstance(block, PictureBlock):
        if not is_jpeg(block.data, block.width, block.height):
            found.append(f"{where}: a picture must be a JPEG image with its width and height")
        return found
    if isinstance(block, HeadingBlock):
        if type(block.level) is not int or not 1 <= block.level <= MAX_LEVEL:
            found.append(f"{where}: a heading's level must be 1 to {MAX_LEVEL}")
        if not is_text(block.label):
            found.append(f"{where}: a heading needs a label")
        if not is_text_or_none(block.title):
            found.append(f"{where}: a heading's title must be text")
        return found

    if not is_text(block.text):
        found.append(f"{where} has no text")
    if not all(is_flag(flag) for flag in (block.verse, block.epigraph, block.attribution)):
        found.append(f"{where}: verse, epigraph and attribution must be true or false")
    if not isinstance(block.lines, list) or not all(isinstance(x, str) for x in block.lines):
        found.append(f"{where}: lines must be a list of text")
    elif block.verse and not block.lines:
        found.append(f"{where}: verse needs its lines")
    if not isinstance(block.notes, dict) or not all(
        isinstance(mark, str) and isinstance(note, str) for mark, note in block.notes.items()
    ):
        found.append(f"{where}: notes must map each mark to a note id")
    return found


def is_text(value: object) -> bool:
    return isinstance(value, str) and value.strip() != ""


def is_text_or_none(value: object) -> bool:
    return value is None or isinstance(value, str)


def is_flag(value: object) -> bool:
    return isinstance(value, bool)


def is_jpeg(data: object, width: object, height: object) -> bool:
    return (
        isinstance(data, bytes)
        and data.startswith(JPEG_START)
        and is_size(width)
        and is_size(height)
    )


def is_size(value: object) -> bool:
    return type(value) is int and value > 0


def without_marks(text: str, marks: Collection[str]) -> str:
    """The text without these note marks, or the space before them: "word [1] next"."""
    if not marks:
        return text
    return re.sub(rf"\s*{NOTE_MARK.pattern}", lambda m: "" if m[1] in marks else m[0], text)
