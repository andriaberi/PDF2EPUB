import re
from dataclasses import dataclass, field

from pdf2epub.pdf import Line, Picture

# "*", "* * *", "⁂", or "---"; a lone dash opens speech.
SCENE_BREAK = re.compile(r"^(?:[*⁂•~=_]\s*)+$|^(?:[—–-]\s*){3,}$")


@dataclass
class Paragraph:
    text: str
    page: int
    lines: list[Line] = field(default_factory=list)
    verse: bool = False
    apart: bool = False
    after_page_gap: bool = False
    epigraph: bool = False
    attribution: bool = False
    # "body", "contents", "preface", "front", "title-page", "reprint" or "back".
    role: str = "body"
    picture: Picture | None = None

    @property
    def scene_break(self) -> bool:
        return is_scene_break(self.text)


def is_scene_break(text: str) -> bool:
    return SCENE_BREAK.match(text) is not None
