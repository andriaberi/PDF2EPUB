from typing import Any

from pdf2epub.pdf.fonts import UNKNOWN, has_unknown, lost_letter, restore_letters


def page(font: str, letters: list[str]) -> list[dict[str, Any]]:
    chars = [{"c": c, "origin": (10.0 * n, 20.0)} for n, c in enumerate(letters)]
    return [{"lines": [{"spans": [{"font": font, "chars": chars}]}]}]


def text(blocks: list[dict[str, Any]]) -> str:
    return "".join(c["c"] for c in blocks[0]["lines"][0]["spans"][0]["chars"])


def test_sylfaen_glyph_numbers_are_georgian_letters() -> None:
    assert lost_letter("Sylfaen", 0x2A8) == "ა"
    assert lost_letter("ABCDEF+Sylfaen-Bold", 0x2AF) == "თ"
    assert lost_letter("Sylfaen", 0x2C8) == "ჰ"
    assert lost_letter("Sylfaen", 0x2C9) is None
    assert lost_letter("Arial", 0x2A8) is None


def test_lost_letters_are_put_back() -> None:
    blocks = page("Sylfaen", [UNKNOWN] * 4 + [" ", "I"])
    assert has_unknown(blocks)
    restore_letters(blocks, page("Sylfaen", ["ʯ", "ʨ", "ʭ", "ʰ", " ", "I"]))
    assert text(blocks) == "თავი I"
    assert not has_unknown(blocks)


def test_letters_of_other_fonts_stay_unknown() -> None:
    blocks = page("Arial", [UNKNOWN])
    restore_letters(blocks, page("Arial", ["ʨ"]))
    assert text(blocks) == UNKNOWN


def test_letters_matched_by_where_they_sit() -> None:
    blocks = page("Sylfaen", [UNKNOWN, UNKNOWN])
    numbered = page("Sylfaen", ["ʨ", "ʩ"])
    numbered[0]["lines"][0]["spans"][0]["chars"].reverse()  # read in another order
    restore_letters(blocks, numbered)
    assert text(blocks) == "აბ"


def test_noto_sans_georgian_opening_quote() -> None:
    assert lost_letter("Noto Sans Georgian", 0x468) == "„"
    assert lost_letter("Noto Sans Georgian", 0x469) is None
