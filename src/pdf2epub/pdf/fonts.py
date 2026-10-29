from typing import Any

# What PyMuPDF reads for a letter the PDF gives no Unicode for.
UNKNOWN = "�"

# Fonts whose glyphs follow the alphabet, so a letter the PDF lost can be worked out
# from its glyph number: font name, its first letter's glyph, that letter, how many.
# Windows' Georgian font, as Word exports it without a Unicode map: ა to ჰ; and the
# opening quote Noto Sans Georgian loses: „.
GLYPH_ORDERS = [("sylfaen", 0x2A8, "ა", 33), ("noto sans georgian", 0x468, "„", 1)]

# Old Georgian fonts that draw each Georgian letter in place of the key a Russian
# keyboard types it with, so the PDF holds those keys: "ithtrbkt,b" is შერეკილები.
# Keys that aren't letters stand for punctuation; any other key is itself.
KEYBOARD_FONTS = ["progtv"]
KEYBOARD = dict(
    zip(
        "f,ultdpsbrkvyjghcneamx[wi/.q'oz];-=_|~@#",
        "აბგდევზთიკლმნოპრსტუფქჩხცშჰყღძწჭჯჟ,.-:?„“",
        strict=True,
    )
)
# A symbol font's keys come in the private use area, from U+F000 up.
SYMBOL_KEYS = 0xF000


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


def type_letters(blocks: list[dict[str, Any]]) -> None:
    """Turn the keys a keyboard font holds into the Georgian letters it shows."""
    for span in spans(blocks):
        if any(name in span["font"].casefold() for name in KEYBOARD_FONTS):
            for char in span["chars"]:
                code = ord(char["c"])
                key = (
                    chr(code - SYMBOL_KEYS)
                    if SYMBOL_KEYS <= code <= SYMBOL_KEYS + 0xFF
                    else char["c"]
                )
                char["c"] = KEYBOARD.get(key, key)


def position(char: dict[str, Any]) -> tuple[float, float]:
    """Where the letter sits, the same however the page is read."""
    x, y = char["origin"]
    return round(x, 2), round(y, 2)


def spans(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [span for block in blocks for line in block.get("lines", []) for span in line["spans"]]
