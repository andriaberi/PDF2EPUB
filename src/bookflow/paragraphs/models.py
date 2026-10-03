from dataclasses import dataclass, field

from bookflow.pdf import Line


@dataclass
class Paragraph:
    text: str
    page: int  # the page it starts on
    lines: list[Line] = field(default_factory=list)  # kept for heading detection
