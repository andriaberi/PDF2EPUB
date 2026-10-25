from typing import Any

# What PyMuPDF reads for a letter the PDF gives no Unicode for.
UNKNOWN = "�"

# Fonts whose glyphs follow the alphabet, so a letter the PDF lost can be worked out
# from its glyph number: font name, its first letter's glyph, that letter, how many.
# Windows' Georgian font, as Word exports it without a Unicode map: ა to ჰ.
GLYPH_ORDERS = [("sylfaen", 0x2A8, "ა", 33)]


def has_unknown(blocks: list[dict[str, Any]]) -> bool:
    return any(char["c"] == UNKNOWN for span in spans(blocks) for char in span["chars"])


def restore_letters(blocks: list[dict[str, Any]], numbered: list[dict[str, Any]]) -> None:
    """Put back the letters the PDF lost, from the same page read with glyph numbers
    in their place, where the font's glyph order is known."""
    glyphs = {position(char): ord(char["c"]) for span in spans(numbered) for char in span["chars"]}
    for span in spans(blocks):
        for char in span["chars"]:
            glyph = glyphs.get(position(char))
            if char["c"] == UNKNOWN and glyph is not None:
                char["c"] = lost_letter(span["font"], glyph) or UNKNOWN


def lost_letter(font: str, glyph: int) -> str | None:
    for name, first_glyph, first_letter, count in GLYPH_ORDERS:
        if name in font.casefold() and first_glyph <= glyph < first_glyph + count:
            return chr(ord(first_letter) + glyph - first_glyph)
    return None


def position(char: dict[str, Any]) -> tuple[float, float]:
    """Where the letter sits, the same however the page is read."""
    x, y = char["origin"]
    return round(x, 2), round(y, 2)


def spans(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [span for block in blocks for line in block.get("lines", []) for span in line["spans"]]
