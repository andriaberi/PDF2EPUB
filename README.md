# Rebind

Converts PDF books into reflowable EPUBs.

Rebind reads the text of a PDF book, drops what only made sense on a printed page (page
numbers, running headers, footnotes), and rebuilds the book as an EPUB 3 with reflowing
paragraphs, one page per chapter, a table of contents and linked notes.

It is written for Georgian books and handles English too.

## Install

Rebind needs Python 3.12 or newer.

```sh
pip install git+https://github.com/andriaberi/Rebind
```

## Use

### The window

Run `rebind` alone to open a window. Drop a PDF onto it or click **Browse…**, check the
title and author, and click **Convert**.

The window uses the system's web view. On Linux, Rebind uses GTK's if Python can reach
it, else Qt's:

```sh
pip install "rebind[qt] @ git+https://github.com/andriaberi/Rebind"  # Qt, any Python
sudo apt install python3-gi gir1.2-webkit2-4.1                       # or GTK, system Python
```

### The command line

```sh
rebind book.pdf
```

This writes `book.epub` next to the PDF and prints what it found:

```
Wrote book.epub: 172 headings, 6317 paragraphs, 206 notes, no cover
```

| Option | What it does |
|---|---|
| `-o`, `--output PATH` | Where to write the EPUB. Default: next to the PDF. |
| `--pages SPEC` | Convert only some pages, 1-based: `1-3,7,10-12`. |
| `--title TEXT` | The book's title. Default: the PDF's metadata, else the file name. |
| `--author TEXT` | The book's author. Default: the PDF's metadata. |
| `--language CODE` | The book's language, such as `ka` or `en`. Default: detected from the text and the PDF's language tag. |
| `--cover IMAGE` | A cover image, used only when the PDF has no cover of its own. |
| `--version` | Print Rebind's version. |

## What it does

- Removes page numbers, running headers, footnotes and OCR specks, and rejoins words
  broken at line ends.
- Rebuilds paragraphs from indents, gaps and short last lines, across page breaks.
- Finds volumes, parts, books and chapters with their titles ("ნაწილი პირველი",
  "Chapter 3", "XII"), plus named sections like a foreword or an epilogue.
- Builds the table of contents from those headings.
- Drops the printed title page and front matter, since the EPUB has its own title page.
- Links notes from a notes section ("შენიშვნები", "Notes", or a list numbered `[1] ...`)
  to their marks in the text.
- Keeps the line breaks of verse.
- Uses the PDF's cover when its first page is a picture.

[How it works](docs/how-it-works.md) describes each step.

## Limits

- Scanned PDFs need a text layer. Run `ocrmypdf` first.
- A heading needs a label word (თავი, ნაწილი, Chapter, Part, ...) and a number, a
  chapter number alone ("XII", "7."), or a section name (წინათქმა, Epilogue, ...).
- Footnotes at the foot of a page are removed, not linked.
- Verse needs at least four lines, or two after a line leading into it (ending with a
  colon, or broken short after a comma).
- Bold, italics and pictures inside the book are not kept.
- Only Georgian and English are detected. Other languages need `--language`.

## License

MIT. The embedded Noto fonts are under the SIL Open Font License
(`src/rebind/epub/fonts/OFL.txt`).
