# PDF2EPUB

Converts PDF books into reflowable EPUBs.

A PDF is laid out for a printed page, so it reads badly on a phone or an e-reader. PDF2EPUB
takes the text of a PDF book and rebuilds it as an EPUB that reflows to any screen, with
chapters, a table of contents and linked notes.

It is made for Georgian books and handles English too.

## Features

- Removes page numbers, running headers, footnotes and website credits
- Rebuilds paragraphs, including ones broken across pages
- Finds volumes, parts and chapters, and builds the table of contents from them
- Links notes to their marks in the text, numbered or starred
- Keeps the line breaks of verse, and sets epigraphs apart under their chapter
- Uses the PDF's cover, or an image you give it

## Installation

PDF2EPUB is a Python library. Add it to a project straight from GitHub:

```sh
uv add "pdf2epub @ git+https://github.com/andriaberi/PDF2EPUB.git"
```

## Usage

```python
from pdf2epub import ConvertError, Options, convert

try:
    result = convert(Options(pdf="book.pdf"), "book.epub", progress=print)
except ConvertError as e:
    print(f"Can't convert: {e}")
else:
    print(result.headings, result.paragraphs, result.notes, result.cover)
```

`convert` calls `progress` with the name of each step as it starts; `STEPS` lists them in
order. It raises `ConvertError` for a PDF, page range or cover it can't read, or an
output it can't write.

To look at the book or change it before it is written, read and write it in two steps:

```python
from pdf2epub import Options, read_book, write_book

book = read_book(Options(pdf="book.pdf"))  # the first three steps
book.metadata.title = "A better title"
write_book(book, "book.epub")
```

A `Book` holds the metadata, the notes, the cover and the book's blocks in reading
order: each a `HeadingBlock` (level, label, title) or a `TextBlock` (a paragraph, verse
with its `lines`, or an epigraph). A heading starts a section that runs to the next one.
Every block has an `id`, the `page` of the PDF it is printed on, and `include`: set it to
`False` to leave the block out of the EPUB. A left-out heading's text joins the section
before it. Writing leaves the book unchanged, so it can be written again.

| Option | Description |
|---|---|
| `pdf` | The PDF book. |
| `pages` | Convert only some pages, such as `"1-3,7,10-12"`. |
| `title` | The book's title. Default: from the PDF, else the file name. |
| `author` | The book's author. Default: from the PDF. |
| `language` | The book's language, such as `"ka"` or `"en"`. Default: detected. |
| `cover` | A cover image, used when the PDF has no cover of its own. |

## Limitations

- Scanned PDFs need a text layer first. `ocrmypdf` can add one.
- Chapters are found by their headings ("თავი I", "Chapter 3", "XII"). A book with
  unusual headings may come out as one long chapter.
- Footnotes at the bottom of a page are removed, not linked.
- Bold, italics and pictures inside the book are not kept.
- Only Georgian and English are detected. For other languages pass `language`.

## Development

From a clone of the repository:

```sh
make install
```

This creates a virtual environment in `.venv` with PDF2EPUB installed from the folder,
so changes take effect at once. To try a book:

```sh
.venv/bin/python scripts/try_book.py book.pdf
```

This writes `book.epub` next to the PDF and says what it found.

| Command | Description |
|---|---|
| `make check` | Lint, type-check and test |
| `make format` | Format the code |
| `make test` | Run the tests |
| `make clean` | Remove caches |

## License

MIT. The embedded Noto fonts are under the SIL Open Font License
(`src/pdf2epub/epub/fonts/OFL.txt`).
