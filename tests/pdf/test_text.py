import pytest

from rebind.pdf.text import clean_text, script_of, strip_edge_debris


def test_collapses_whitespace() -> None:
    assert clean_text("  one   two\tthree ") == "one two three"


def test_composes_to_nfc() -> None:
    assert clean_text("cafe\u0301") == "café"


def test_expands_ligatures() -> None:
    assert clean_text("\ufb01nal") == "final"


def test_drops_invisible_characters() -> None:
    assert clean_text("a\u200bb\ufeffc\u200dd") == "abcd"


def test_ocr_dash_runs_become_one_dash() -> None:
    assert clean_text("–- ვინ არის, –– მიუგო") == "— ვინ არის, — მიუგო"


@pytest.mark.parametrize(
    ("text", "joined"),
    [
        ("IV წ ი გ ნ ი", "IV წიგნი"),
        ("თ ა ლ ე ჲ ა", "თალეჲა"),
        ("C h a p t e r 3", "Chapter 3"),
        ("- პ უ რ ი!", "- პური!"),
        ("ე ბ ი.", "ე ბ ი."),  # the end of a word wrapped from the line above
        ("„ჟ ი ვ ი ო!“", "„ჟივიო!“"),
        ("ე ბ ი. – თქვა მან", "ე ბ ი. – თქვა მან"),
        ("ა და ბ", "ა და ბ"),  # one-letter words in prose stay apart
        ("თქვა სიტყვა ფ ა ქ ტ", "თქვა სიტყვა ფ ა ქ ტ"),  # emphasis in the text stays
        ("J. R. R. Tolkien", "J. R. R. Tolkien"),
    ],
)
def test_joins_letter_spaced_words(text: str, joined: str) -> None:
    assert clean_text(text) == joined


def test_line_end_hyphen_is_normalised() -> None:
    assert clean_text("ატე–-") == "ატე-"
    assert clean_text("მოთხრო–") == "მოთხრო-"
    assert clean_text("hyphen\u00ad") == "hyphen-"


def test_dash_after_a_space_at_line_end_is_a_dash() -> None:
    assert clean_text("ვაებით. –-") == "ვაებით. —"


def test_keeps_inner_hyphens() -> None:
    assert clean_text("შარლ-ფრანსუა") == "შარლ-ფრანსუა"


def test_drops_middle_dots() -> None:
    assert clean_text("თავის ·ქცევით ·") == "თავის ქცევით"
    assert clean_text("ჰკეტენ·პარადოქსი") == "ჰკეტენ პარადოქსი"


def test_script_of() -> None:
    assert script_of("ა") == "GEORGIAN"
    assert script_of("a") == "LATIN"
    assert script_of("1") is None


@pytest.mark.parametrize(
    ("text", "cleaned"),
    [
        ("' ლივრი", "ლივრი"),
        ("| — მარკიზ მონკალმი", "— მარკიზ მონკალმი"),
        (", ჟავერი არ დაიძრა.", "ჟავერი არ დაიძრა."),
        ("მიპოვა უკვდავი სახელი. '", "მიპოვა უკვდავი სახელი."),
        ("ეტყოდა: |", "ეტყოდა:"),
        ("'ზოგიერთ ფენებში", "ზოგიერთ ფენებში"),
        ('"და დიდი', "და დიდი"),
        (",", ""),
    ],
)
def test_strips_edge_debris(text: str, cleaned: str) -> None:
    assert strip_edge_debris(text) == cleaned


@pytest.mark.parametrize(
    "text",
    ['"Hello," he said.', "It's fine.", "# 94601 იყო", "თქვა: —", "„საბრალონი“,"],
)
def test_keeps_real_edges(text: str) -> None:
    assert strip_edge_debris(text) == text
