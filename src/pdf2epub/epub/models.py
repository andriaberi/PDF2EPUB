from dataclasses import dataclass


@dataclass
class Metadata:
    title: str
    author: str | None
    language: str
    identifier: str  # stays the same when the same book is converted again
