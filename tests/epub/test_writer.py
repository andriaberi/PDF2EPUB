import zipfile
from pathlib import Path
from xml.dom import minidom
from xml.etree import ElementTree

from rebind.cover import Cover
from rebind.epub import Metadata, write_epub
from rebind.paragraphs import Paragraph
from rebind.pdf import Line
from rebind.structure import Heading, Note, Section

METADATA = Metadata(title="საბრალონი", author="ვიქტორ ჰიუგო", language="ka", identifier="urn:x")


def paragraph(text: str) -> Paragraph:
    return Paragraph(text, 1)


SECTIONS = [
    Section(None, [paragraph("წინასიტყვაობა & <შესავალი>")]),
    Section(Heading(1, "წიგნი პირველი", "კაცი მართალი")),
    Section(Heading(2, "თავი პირველი", "ბატონი მირიელი"), [paragraph("ერთი."), paragraph("ორი.")]),
    Section(Heading(2, "თავი მეორე"), [paragraph("სამი.")]),
    Section(Heading(1, "წიგნი მეორე")),
    Section(Heading(2, "თავი პირველი"), [paragraph("ოთხი.")]),
]


def written(tmp_path: Path) -> zipfile.ZipFile:
    path = tmp_path / "book.epub"
    write_epub(path, SECTIONS, METADATA)
    return zipfile.ZipFile(path)


def test_mimetype_comes_first_uncompressed(tmp_path: Path) -> None:
    epub = written(tmp_path)
    first = epub.infolist()[0]
    assert first.filename == "mimetype"
    assert first.compress_type == zipfile.ZIP_STORED
    assert epub.read("mimetype") == b"application/epub+zip"


def test_every_file_is_well_formed_xml(tmp_path: Path) -> None:
    epub = written(tmp_path)
    for name in epub.namelist():
        if name.endswith((".xhtml", ".opf", ".ncx", ".xml")):
            minidom.parseString(epub.read(name))


def test_each_section_is_its_own_page(tmp_path: Path) -> None:
    epub = written(tmp_path)
    pages = sorted(n for n in epub.namelist() if n.startswith("EPUB/text/"))
    assert len(pages) == len(SECTIONS)
    chapter = epub.read(pages[2]).decode()
    assert '<h2><span class="label">თავი პირველი</span>ბატონი მირიელი</h2>' in chapter
    assert "<p>ერთი.</p>" in chapter


def test_text_is_escaped(tmp_path: Path) -> None:
    front = written(tmp_path).read("EPUB/text/section-0001.xhtml").decode()
    assert "წინასიტყვაობა &amp; &lt;შესავალი&gt;" in front


def test_language_is_set_everywhere(tmp_path: Path) -> None:
    epub = written(tmp_path)
    assert "<dc:language>ka</dc:language>" in epub.read("EPUB/content.opf").decode()
    assert 'xml:lang="ka"' in epub.read("EPUB/text/section-0003.xhtml").decode()


def test_table_of_contents_is_nested(tmp_path: Path) -> None:
    nav = ElementTree.fromstring(written(tmp_path).read("EPUB/nav.xhtml"))
    xhtml = "{http://www.w3.org/1999/xhtml}"

    def text(link: ElementTree.Element) -> str:
        return "".join(link.itertext())

    books = nav.findall(f".//{xhtml}nav/{xhtml}ol/{xhtml}li")
    assert [text(book.find(f"{xhtml}a")) for book in books] == [  # type: ignore[arg-type]
        "წიგნი პირველი: კაცი მართალი",
        "წიგნი მეორე",
    ]
    chapters = books[0].findall(f"{xhtml}ol/{xhtml}li/{xhtml}a")
    assert [text(chapter) for chapter in chapters] == [
        "თავი პირველი: ბატონი მირიელი",
        "თავი მეორე",
    ]


def test_contents_marks_parts_holding_chapters(tmp_path: Path) -> None:
    nav = written(tmp_path).read("EPUB/nav.xhtml").decode()
    assert '<li class="group"><a href="text/section-0002.xhtml"><span class="label">' in nav
    assert '<span class="label">თავი პირველი:</span> ბატონი მირიელი</a>' in nav


def test_heading_without_title_shows_its_label_as_the_title(tmp_path: Path) -> None:
    chapter = written(tmp_path).read("EPUB/text/section-0004.xhtml").decode()
    assert "<h2>თავი მეორე</h2>" in chapter


def test_fonts_are_embedded(tmp_path: Path) -> None:
    epub = written(tmp_path)
    assert "EPUB/fonts/NotoSerifGeorgian-Regular.ttf" in epub.namelist()
    assert 'media-type="font/ttf"' in epub.read("EPUB/content.opf").decode()
    assert "url(fonts/NotoSerifGeorgian-Regular.ttf)" in epub.read("EPUB/style.css").decode()


def test_contents_is_a_page_of_the_book(tmp_path: Path) -> None:
    opf = written(tmp_path).read("EPUB/content.opf").decode()
    assert '<itemref idref="title"/>\n<itemref idref="nav"/>' in opf
    assert "<h1>სარჩევი</h1>" in written(tmp_path).read("EPUB/nav.xhtml").decode()


def test_cover_comes_first(tmp_path: Path) -> None:
    path = tmp_path / "book.epub"
    write_epub(path, SECTIONS, METADATA, Cover(b"\xff\xd8jpeg", 600, 900))
    epub = zipfile.ZipFile(path)
    assert epub.read("EPUB/images/cover.jpg") == b"\xff\xd8jpeg"
    opf = epub.read("EPUB/content.opf").decode()
    assert 'properties="cover-image"' in opf
    assert '<meta name="cover" content="cover-image"/>' in opf
    assert '<spine toc="ncx">\n<itemref idref="cover"/>' in opf
    page = epub.read("EPUB/cover.xhtml").decode()
    assert 'viewBox="0 0 600 900"' in page
    minidom.parseString(page)


def test_no_cover_without_one(tmp_path: Path) -> None:
    epub = written(tmp_path)
    assert "EPUB/cover.xhtml" not in epub.namelist()
    assert "cover-image" not in epub.read("EPUB/content.opf").decode()


def test_notes_get_a_page_and_marks_link_to_them(tmp_path: Path) -> None:
    note = Note("note-1", "1", "ფრეილინა – მხლებელი.")
    chapter = Section(Heading(1, "თავი პირველი"), [paragraph("ფრეილინა[1] & [2].")])
    chapter.notes["1"] = note
    path = tmp_path / "book.epub"
    write_epub(path, [chapter], METADATA, notes=[note])
    epub = zipfile.ZipFile(path)

    text = epub.read("EPUB/text/section-0001.xhtml").decode()
    assert 'id="ref-note-1" href="../notes.xhtml#note-1">1</a> &amp; [2].' in text
    notes = epub.read("EPUB/notes.xhtml").decode()
    assert '<li id="note-1" epub:type="endnote">' in notes
    assert 'href="text/section-0001.xhtml#ref-note-1"' in notes
    minidom.parseString(notes)
    assert '<itemref idref="notes"/>' in epub.read("EPUB/content.opf").decode()
    assert '<a href="notes.xhtml">' in epub.read("EPUB/nav.xhtml").decode()


def test_no_notes_page_without_notes(tmp_path: Path) -> None:
    assert "EPUB/notes.xhtml" not in written(tmp_path).namelist()


def test_verse_keeps_its_line_breaks(tmp_path: Path) -> None:
    lines = [Line(text, 0, 0, 0, 0) for text in ("ერთი,", "ორი & სამი")]
    verse = Paragraph("ერთი, ორი & სამი", 1, lines, verse=True)
    path = tmp_path / "book.epub"
    write_epub(path, [Section(Heading(1, "თავი პირველი"), [verse])], METADATA)
    text = zipfile.ZipFile(path).read("EPUB/text/section-0001.xhtml").decode()
    assert '<div class="verse"><p>ერთი,</p><p>ორი &amp; სამი</p></div>' in text
