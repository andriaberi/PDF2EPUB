# PDF2EPUB

Converts PDF books into reflowable EPUBs.

A PDF is laid out for a printed page, so it reads badly on a phone or an e-reader. PDF2EPUB
takes the text of a PDF book and rebuilds it as an EPUB that reflows to any screen, with
chapters, a table of contents and linked notes.

It is made for Georgian books and handles English too.

## Features

- Removes page numbers, running headers, footnotes and website credits
- Rebuilds paragraphs, including ones broken across pages
- Finds volumes, parts and chapters, and builds the table of contents from them. It
  follows the PDF's own outline when that matches the text; a book with no headings
  gets numbered chapters wherever it leaves a blank line
- Links notes to their marks in the text, numbered or starred
- Keeps the line breaks of verse, and sets epigraphs apart under their chapter
- Uses the PDF's cover, or an image you give it
- Reads the Georgian letters of Word PDFs set in Sylfaen that lost them

## Installation

PDF2EPUB is a Python library. Add it to a project straight from GitHub:

```sh
uv add "pdf2epub @ git+https://github.com/andriaberi/PDF2EPUB.git"
```

### Versions

Every change to `main` that passes the checks is released on its own, numbered by the
day: `2026.1025.1` is the first release of 25 October 2026, `2026.1025.2` the second,
and 5 January 2027 starts at `2027.105.1`. Each is a tag and a
[GitHub release](https://github.com/andriaberi/PDF2EPUB/releases) with its changes
listed. To stay on one release, name its tag:

```sh
uv add "pdf2epub @ git+https://github.com/andriaberi/PDF2EPUB.git@v2026.1025.1"
```

The installed version is `pdf2epub.__version__`.

## Usage

### Converting

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
order.

| Option | Description |
|---|---|
| `pdf` | The PDF book. |
| `pages` | Convert only some pages, such as `"1-3,7,10-12"`. |
| `title` | The book's title. Default: from the PDF, else the file name. |
| `author` | The book's author. Default: from the PDF. |
| `language` | The book's language, such as `"ka"` or `"en"`. Default: detected. |
| `cover` | A cover image, a path or its bytes, used when the PDF has no cover of its own. |

The EPUB can be written to a path or to a binary file object such as `io.BytesIO`.

### Editing before writing

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

A block's `role` says where it belongs. Only the body is included at first; the rest
is found and kept, to be included if wanted:

| Role | What it is |
|---|---|
| `body` | The book itself |
| `contents` | The printed table of contents, a block per page, line by line |
| `preface` | A foreword or preface, with its heading |
| `front` | Other text before the first heading: credits, a translator's note |
| `title-page` | The book's own title page, or its title and author repeated |
| `reprint` | The title page printed again before a later volume |
| `back` | Who translated or published the book, and when, after its last line |

Set `book.include_notes = False` to write the book without its notes; removing a note
from `book.notes` leaves out that note alone. Either way the marks that pointed to it
are taken out of the text.

`book.set_cover(image)` replaces the cover with an image, a path or its bytes.
`render_page("book.pdf", block.page, width=800)` gives a page of the PDF as a PNG, to
show next to the blocks printed on it.

### Keeping the book between requests

`book.to_dict()` gives the book as JSON-able data, and `Book.from_dict(data)` reads it
back. Data of another version, or with a part missing or of the wrong kind, raises
`BookError`.

`book.problems()` lists what an edit has broken, such as a heading without a label, an
unknown role or nothing left to write; `write_book` refuses a book with problems.

### Errors

Every error is a `ConvertError` with a message to show: a PDF, page or cover that can't
be read, an output that can't be written, or a `BookError` for book data that can't be
used.

## Limitations

- Scanned PDFs need a text layer first. `ocrmypdf` can add one.
- Chapters are found by their headings ("თავი I", "Chapter 3", "XII"), or by blank
  lines in a book with none. A blank line at the top or bottom of a page can't be
  seen, so such a chapter break is missed. A book with neither comes out as one text,
  listed by its title.
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
