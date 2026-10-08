import re
from dataclasses import dataclass, field

from pdf2epub.pdf import Line

# A scene break: "*", "* * *", "⁂", or a row of three dashes or more. A dash alone
# opens speech instead.
SCENE_BREAK = re.compile(r"^(?:[*⁂•~=_]\s*)+$|^(?:[—–-]\s*){3,}$")


@dataclass
class Paragraph:
    text: str
    page: int  # the page it starts on
    lines: list[Line] = field(default_factory=list)  # kept for heading detection
    verse: bool = False  # keeps its line breaks: a poem, a list
    # Starts far below the finished text above it, as a heading set in the text does.
    apart: bool = False

    @property
    def scene_break(self) -> bool:
        return is_scene_break(self.text)


def is_scene_break(text: str) -> bool:
    return SCENE_BREAK.match(text) is not None
