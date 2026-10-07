from rebind.pdf import Line, Page
from rebind.structure import drop_printed_contents


def page(number: int, texts: list[str]) -> Page:
    lines = [Line(text, 45, 40 + 14 * row, 385, 50 + 14 * row) for row, text in enumerate(texts)]
    return Page(number, 430, 590, lines)


TEXT = page(1, ["ტექსტი, რომელიც გრძელდება"] * 20)


def test_page_of_entries_with_page_numbers_is_dropped() -> None:
    contents = page(9, [f"თავი {word} ........ {number}" for number, word in enumerate("abcdef")])
    assert drop_printed_contents([TEXT, contents]) == [TEXT]


def test_titled_contents_listing_labels_and_titles_is_dropped() -> None:
    contents = page(9, ["სარჩევი", "ნაწილი პირველი", "ფანტინი", "წიგნი პირველი", "კაცი მართალი"])
    contents.lines += page(9, ["თავი პირველი", "ბატონი მირიელი"]).lines
    assert drop_printed_contents([TEXT, contents]) == [TEXT]


def test_text_with_a_few_numbers_is_kept() -> None:
    years = page(2, ["ისე იყო 1832", "წელს და 1833", *["ტექსტი გრძელდება"] * 18])
    assert drop_printed_contents([TEXT, years]) == [TEXT, years]


def test_chapter_opening_is_kept() -> None:
    opening = page(3, ["თავი მეორე", "ბატონი მირიელი", *["ტექსტი გრძელდება"] * 25])
    assert drop_printed_contents([opening]) == [opening]
