from typing import Any

# PyMuPDF's stand-in for a letter with no Unicode.
UNKNOWN = "�"

# Font name, its first letter's glyph, that letter, how many.
GLYPH_ORDERS = [("sylfaen", 0x2A8, "ა", 33), ("noto sans georgian", 0x468, "„", 1)]

# Old Georgian fonts typed on Russian keys: "ithtrbkt,b" is შერეკილები.
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
    x, y = char["origin"]
    return round(x, 2), round(y, 2)


def spans(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [span for block in blocks for line in block.get("lines", []) for span in line["spans"]]
