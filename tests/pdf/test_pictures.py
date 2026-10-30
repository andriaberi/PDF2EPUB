from collections.abc import Callable

from pdf2epub.pdf import read_pdf

MakePdf = Callable[..., str]


def test_reads_a_picture_where_it_is_printed(make_picture_pdf: MakePdf) -> None:
    book = read_pdf(make_picture_pdf({1: [(100, 200, 300, 300)]}))
    (picture,) = book.pages[1].pictures
    assert (round(picture.y0), round(picture.y1)) == (200, 300)
    assert picture.data.startswith(b"\xff\xd8")
    assert picture.width / picture.height == 2
    assert not any(page.pictures for page in book.pages if page.number != 2)


def test_lines_printed_on_a_picture_are_its_own(make_picture_pdf: MakePdf) -> None:
    book = read_pdf(make_picture_pdf({1: [(100, 200, 300, 300)]}, labels=2))
    assert book.pages[1].pictures
    assert not any(line.text == "Label" for line in book.pages[1].lines)


def test_a_picture_under_much_text_is_a_background(make_picture_pdf: MakePdf) -> None:
    book = read_pdf(make_picture_pdf({1: [(40, 100, 360, 400)]}, labels=6))
    assert not book.pages[1].pictures
    assert sum(line.text == "Label" for line in book.pages[1].lines) == 6


def test_an_ornament_is_no_picture(make_picture_pdf: MakePdf) -> None:
    book = read_pdf(make_picture_pdf({1: [(180, 200, 220, 220)]}))
    assert not book.pages[1].pictures


def test_a_picture_on_every_page_is_a_logo(make_picture_pdf: MakePdf) -> None:
    logo = [(150, 20, 250, 50)]
    book = read_pdf(make_picture_pdf(dict.fromkeys(range(4), logo)))
    assert not any(page.pictures for page in book.pages)


def test_strips_of_one_picture_make_one(make_picture_pdf: MakePdf) -> None:
    strips = [(100, 200 + 25 * row, 300, 225 + 25 * row) for row in range(4)]
    (picture,) = read_pdf(make_picture_pdf({1: strips})).pages[1].pictures
    assert (round(picture.y0), round(picture.y1)) == (200, 300)
