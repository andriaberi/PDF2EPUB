# Bookflow

A fast, clean Python tool for converting PDF books into well-structured, reflowable EPUBs.

Bookflow reads the text of a PDF book, throws away what only made sense on a printed page
(page numbers, running headers, the printed table of contents), and rebuilds the book as
an EPUB 3: paragraphs that reflow on any screen, one page per chapter, a working table of
contents, linked notes, and verse that keeps its lines.

It is written with Georgian books in mind and handles English too.

## Install

Bookflow needs Python 3.12 or newer.

```sh
pip install git+https://github.com/andriaberi/Bookflow
```

Or from a clone, for working on it: `make install` (see [Development](docs/development.md)).

## Use

### The window

```sh
bookflow
```

Run alone, `bookflow` opens a window:

1. **Drop a PDF** onto the window, or click **Browse…**. It shows the file's page count
   and size.
2. **Check the details.** Title and author come from the PDF where it has them. You can
   also set the language, a page range, a cover image for PDFs without one, and where
   to save.
3. Click **Convert**. A progress bar and status line follow each step; when it's done,
   it shows what it found with **Show in folder** and **Convert another**. If something
   goes wrong, the status line says why.

The window follows your system's light or dark mode.

The window is a web page shown in your system's own web view: Windows and macOS have
one built in. On Linux, Bookflow uses GTK's when Python can reach it, else Qt's:

```sh
pip install "bookflow[qt]"                      # Qt's web view: works in any Python
sudo apt install python3-gi gir1.2-webkit2-4.1  # or GTK's, for the system's Python
```

### The command line

```sh
bookflow book.pdf
```

This writes `book.epub` next to the PDF and prints what it found:

```
Wrote book.epub: 160 headings, 5977 paragraphs, 206 notes, cover from the PDF
```

Options work the same as the window's fields:

| Option | What it does |
|---|---|
| `-o`, `--output PATH` | Where to write the EPUB. Default: next to the PDF, with `.epub`. |
| `--pages SPEC` | Convert only some pages, 1-based: `1-3,7,10-12`. |
| `--title TEXT` | The book's title. Default: the PDF's metadata, else the file name. |
| `--author TEXT` | The book's author. Default: the PDF's metadata. |
| `--language CODE` | The book's language, such as `ka` or `en`. Default: the PDF's own language tag, else detected from the text. |
| `--cover IMAGE` | A cover image (JPEG, PNG, ...) for books whose PDF has no cover. A PDF that has one keeps its own. |
| `--version` | Print Bookflow's version. |

Many PDFs have no title or author in their metadata, so the title page would read
`book`. Pass `--title` and `--author` to fix that:

```sh
bookflow ucxo.pdf --title "უცხო" --author "ალბერ კამიუ"
```

## What Bookflow does with a book

- **Cleans the text.** Page numbers, running headers and footers, OCR specks and
  dashes misread as two, words broken at line ends, ligatures. It puts back the spaces
  in PDFs that set words apart by position alone.
- **Rebuilds paragraphs** from indents, gaps and short last lines, across page breaks.
- **Finds the book's divisions.** These are volumes, parts, books and chapters, with
  their titles: "ნაწილი პირველი", "თავი მეორე: ...", "Chapter 3", or chapters numbered
  "I", "II", ... Forewords, prologues and epilogues get headings too. Headings may be
  centred, flush left, flush right or in a bigger font, with the title below the label
  or on the same line.
- **Builds the table of contents** from those headings and drops the printed one.
- **Drops the printed title page** and other front matter before the first heading,
  since the EPUB has its own title page.
- **Links notes.** A notes section ("შენიშვნები", "Notes") with `[1] ...` entries
  becomes a notes page, and each mark in the text links to its note and back.
- **Keeps verse and lists line by line**, with stanzas apart.
- **Uses the PDF's cover** when its first page is a picture, or the `--cover` image.
- **Embeds fonts** (Noto Serif, Noto Serif Georgian) so every reader shows the same type.

[How it works](docs/how-it-works.md) explains each step and the rules behind it.

## Limits

- **Scanned PDFs need a text layer.** Bookflow reads text and doesn't do OCR itself.
  Run `ocrmypdf` first.
- **Headings need a label word, a number or a section name.** A heading is a word like
  თავი, ნაწილი, Chapter or Part plus one number word, a chapter number alone ("XII",
  "7."), or a named section such as წინათქმა, ეპილოგი, Preface or Epilogue.
- **Footnotes at the foot of a page are removed, not linked.** Only notes collected in
  a notes section are linked.
- **Verse needs at least four lines.** Shorter verse, such as couplets, reads as text.
  Letters come out as ordinary paragraphs.
- **Bold, italics and pictures inside the book are not kept yet.**
- **Only Georgian and English** are detected. Other languages need `--language`.

## License

MIT. The embedded Noto fonts are under the SIL Open Font License
(`src/bookflow/epub/fonts/OFL.txt`).
