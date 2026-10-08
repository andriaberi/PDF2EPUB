from pathlib import Path

import pymupdf
import pytest

from pdf2epub.cover import Cover, CoverError, find_cover, load_cover


def image_file(tmp_path: Path, name: str = "cover.png", alpha: bool = True) -> str:
    doc = pymupdf.open()
    page = doc.new_page(width=60, height=90)
    page.draw_rect(page.rect, color=None, fill=(0.2, 0.3, 0.5))
    path = tmp_path / name
    page.get_pixmap(alpha=alpha).save(path)
    return str(path)


def pdf_with_first_page(tmp_path: Path, picture: bool, words: int = 0) -> str:
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=600)
    if picture:
        page.insert_image(page.rect, filename=image_file(tmp_path))
    for row in range(words // 5):
        page.insert_text((40, 40 + 14 * row), "one two three four five", fontsize=9)
    doc.new_page().insert_text((40, 40), "Chapter text.")
    path = tmp_path / "book.pdf"
    doc.save(path)
    return str(path)


def is_jpeg(cover: Cover) -> bool:
    return cover.data[:2] == b"\xff\xd8"


def test_loads_png_with_transparency_as_jpeg(tmp_path: Path) -> None:
    cover = load_cover(image_file(tmp_path))
    assert is_jpeg(cover)
    assert (cover.width, cover.height) == (60, 90)


def test_loads_jpeg(tmp_path: Path) -> None:
    assert is_jpeg(load_cover(image_file(tmp_path, "cover.jpg", alpha=False)))


def test_missing_cover_file(tmp_path: Path) -> None:
    with pytest.raises(CoverError, match="no such cover image"):
        load_cover(str(tmp_path / "missing.png"))


def test_file_that_is_not_an_image(tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("hello")
    with pytest.raises(CoverError, match="not an image"):
        load_cover(str(path))


def test_picture_first_page_is_the_cover(tmp_path: Path) -> None:
    cover = find_cover(pdf_with_first_page(tmp_path, picture=True, words=5))
    assert cover is not None
    assert is_jpeg(cover)
    assert cover.height == 1600


def test_text_first_page_is_not_a_cover(tmp_path: Path) -> None:
    assert find_cover(pdf_with_first_page(tmp_path, picture=False, words=50)) is None


def test_scanned_title_page_with_text_is_not_a_cover(tmp_path: Path) -> None:
    assert find_cover(pdf_with_first_page(tmp_path, picture=True, words=40)) is None
