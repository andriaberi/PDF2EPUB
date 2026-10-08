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

PDF2EPUB needs Python 3.12 or newer. From the project folder:

```sh
make install
```

This creates a virtual environment in `.venv` with PDF2EPUB installed.

On Linux the window also needs a web view: either GTK's or Qt's.

```sh
sudo apt install python3-gi gir1.2-webkit2-4.1  # GTK
.venv/bin/pip install -e ".[qt]"                # or Qt
```

## Usage

### Window

```sh
.venv/bin/pdf2epub
```

Drop a PDF onto the window or click **Browse…**, check the title and author, and click
**Convert**.

### Command line

```sh
.venv/bin/pdf2epub book.pdf
```

This writes `book.epub` next to the PDF:

```
Wrote book.epub: 172 headings, 6317 paragraphs, 206 notes, no cover
```

| Option | Description |
|---|---|
| `-o`, `--output PATH` | Where to write the EPUB. Default: next to the PDF. |
| `--pages SPEC` | Convert only some pages, such as `1-3,7,10-12`. |
| `--title TEXT` | The book's title. Default: from the PDF, else the file name. |
| `--author TEXT` | The book's author. Default: from the PDF. |
| `--language CODE` | The book's language, such as `ka` or `en`. Default: detected. |
| `--cover IMAGE` | A cover image, used when the PDF has no cover of its own. |

## Limitations

- Scanned PDFs need a text layer first. `ocrmypdf` can add one.
- Chapters are found by their headings ("თავი I", "Chapter 3", "XII"). A book with
  unusual headings may come out as one long chapter.
- Footnotes at the bottom of a page are removed, not linked.
- Bold, italics and pictures inside the book are not kept.
- Only Georgian and English are detected. For other languages use `--language`.

## Development

| Command | Description |
|---|---|
| `make check` | Lint, type-check and test |
| `make format` | Format the code |
| `make test` | Run the tests |
| `make clean` | Remove caches |

## License

MIT. The embedded Noto fonts are under the SIL Open Font License
(`src/pdf2epub/epub/fonts/OFL.txt`).
