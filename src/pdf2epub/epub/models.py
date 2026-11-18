from dataclasses import dataclass


@dataclass
class Metadata:
    title: str
    author: str | None
    language: str
    identifier: str  # stable across reconversions
