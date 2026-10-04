# How Bookflow works

Bookflow turns a PDF into an EPUB in stages. Each stage takes the previous one's
output and knows nothing about the stages after it:

```
PDF ─► pdf/ ─► contents ─► paragraphs/ ─► structure/ ─► notes ─► epub/ ─► EPUB
       lines   drop the    paragraphs,    sections     linked     pages, contents,
       per     printed     verse          (headings    notes      notes, cover,
       page    contents                   + text)                 fonts
```

`pipeline.py` runs the stages in this order. Measurements are in PDF points. Most
thresholds are in **line heights** (the median height of a line of text), so they work
the same at any font size.

The rules are layout rules, so most of them compare a line with the book's usual
**text column**: the median left edge, right edge, line height and line gap of pages
with at least ten lines.

## 1. Reading the PDF (`pdf/`)

`read_pdf` opens the PDF with PyMuPDF and returns a `Book`: title, author, language and
a list of `Page`s, each a list of `Line`s with their text and position.

- **Lines.** PyMuPDF can split one printed line into several pieces. Pieces on the same
  row are joined left to right (`merge_rows`).
- **Text cleaning** (`text.py`) is done line by line:
  - Unicode NFC, with ligatures (`ﬁ`) spelled out and invisible characters removed.
  - Runs of dashes that OCR made from one ("–-") become one em dash.
  - A word broken at the line end keeps a plain `-`, so the paragraph stage can rejoin it.
  - Stray middle dots become spaces.
- **Noise** (`noise.py`) is removed page by page:
  - **Junk lines:** OCR misreads of pictures and stains, meaning lines with no real word,
    or with more broken words than real ones.
  - **Page numbers:** short lines with no word, in the top or bottom 12% of the page.
  - **Running headers and footers:** edge lines whose words repeat on 3 or more pages.
    Digits are ignored, so "Chapter 3 · 41" and "Chapter 3 · 42" match.
  - **Glued page numbers:** OCR sometimes puts the page number on the line next to it.
    These are found once the printed numbers' offset from the PDF's page numbers is known.
  - **Footnotes:** a block of at most 6 lines at the foot of the page, below a wide gap,
    starting with a reference mark. They are kept apart in `Page.footnotes` and are
    not in the EPUB yet.
- **Language:** the PDF's `/Lang` tag if it has one, else the script most of the text is
  written in (Georgian → `ka`, Latin → `en`). `--language` overrides both.

## 2. Dropping the printed contents (`structure/contents.py`)

A printed table of contents would turn into a list of fake headings, so its pages are
dropped before paragraphs are built. A line is an **entry** if:
- it ends in a page number after a space or dot leaders ("თავი მესამე ....... 45"), or
- it is a label alone ("თავი მესამე").

A page counts as contents if one of these holds:
- **5 or more entries, at least half of its lines**, or
- **it starts with a contents title** (სარჩევი, შინაარსი, Contents, Table of Contents)
  and has 3 or more entries, at least 30% of its lines.

The second rule allows for titles that take up lines between entries.

## 3. Paragraphs (`paragraphs/`)

`build_paragraphs` joins lines into `Paragraph`s across pages. Each page is measured on
its own (`measure`), because scans drift. A page of dialogue or verse has few full
lines, though, and would mistake its indent for its margin. If a page's left edge is
more than 0.8 line heights inside the book's, or its right edge more than 2 line
heights short of it, the page uses the book's column instead (`fit`).

A line **starts a new paragraph** if any of these is true. The first rule that applies
wins:

1. The line above ends in a broken word: **never a new paragraph**.
2. Either this line or the one above is tall (more than 1.3× the usual height): a heading.
3. The line above starts more than 4 line heights to the right of this one. It was
   centred or flush right, like a heading.
4. The line is indented by more than 0.8 line heights.
5. There is a gap above it wider than the usual gap plus 0.8 line heights.
6. It is the first line of a page, and the last page's text stopped above 75% of the
   page height (a chapter end).
7. The line above ends a sentence and stops more than 2 line heights short of the
   right edge.

Words broken at a line end are rejoined ("დარჩე-" + "ნია" → "დარჩენია").

### Verse and lists (`paragraphs/verse.py`)

Songs, poems, lists and inscriptions lose their sense when their lines run together,
so they become **verse paragraphs**. These keep each line as printed. A run of lines
on a page is verse if:

- **It has at least 4 lines,** each:
  - stopping more than 4 line heights short of the right edge,
  - not starting with a dialogue dash (`-`, `–`, `—`),
  - not tall, and
  - not a chapter label.
- **At most half of them end a sentence** (`.`, `!`, `?`, `…`, before any closing
  quote). Short lines that each end a sentence are short paragraphs of text, such as
  quick dialogue or narration.

Text that leads into the verse is trimmed off its start first:
- the last line of the paragraph above (no indent, no gap before it), and
- short lines ending a sentence or with a colon ("…ლექსი დაუწერა:").

**Stanzas** are split where the gap between two verse lines is wider than the verse's
own usual gap plus 0.8 line heights. The verse's own gap matters because some books
space verse wider than prose.

## 4. Structure (`structure/`)

`build_sections` splits the paragraphs into `Section`s, each a `Heading` and the
paragraphs up to the next one. Text before the first heading is front matter.

### Labels

A **label** is a division word plus one number word, alone on its line
(`bookflow/labels.py`):

| Level | Georgian | English |
|---|---|---|
| 1 | ტომი | Volume |
| 2 | ნაწილი | Part |
| 3 | წიგნი | Book |
| 4 | თავი | Chapter |

- The number may come first ("მესამე ნაწილი"), but then only an exact spelling of the
  label word counts.
- With the label first, one misread letter is allowed ("თაჭი მეორე" is fixed to
  "თავი მეორე").
- Only a numeral may have a full stop after it ("Chapter 12.", "CHAPTER XII."). That
  keeps sentences such as "თავი დახარა." out.
- The levels a book uses are renumbered from 1. A book of chapters only has every
  chapter at level 1.
- The label word is put in the same place throughout the contents, whichever order
  most of the book uses.

The label's line can be placed **any way except as a full line of running text**:
centred, flush left, flush right, or in a bigger font. Books differ, and only a line
that runs from the margin to the right edge rules a label out.

### Titles

The paragraphs after a label are its **title** if they:

- are at most 3 lines in all,
- are each centred or short,
- are on the same page as the label,
- don't end with a colon, which leads into speech, and
- are set off from the text after them, either by being centred or by a gap.

A label in a big font takes only a title in the same big font. The next line in text
size is the chapter's first line, and the chapter has no title.

When a title has run into the first paragraph, as across a page break, the paragraph's
short first line is split off as the title.

### Front matter

- **Title page:** front matter of at most 3 paragraphs on one page, with none ending
  a sentence, is the book's own title page. It is dropped because the EPUB
  makes its own. Lines repeating the title or author are dropped too.
- **Title page reprints:** a title page printed again before a later volume is
  removed from the end of the section before it.

## 5. Notes (`structure/notes.py`)

A notes section is a paragraph reading შენიშვნები, Notes or Endnotes, followed by
paragraphs starting with a mark: `[12] ფრეილინა – ...`.

- **Where it ends:** the section runs to the last paragraph that starts with a mark.
  Paragraphs in between belong to the note before them, since long notes go on.
- **Splitting:** notes printed one under another often read as one paragraph, so the
  text is split at every `[n]` that follows a space. A stray digit right after the
  mark (`[24]1`) is dropped.
- **Linking:** marks in the text (`ფრეილინა[12]`) before a notes section link to that
  section. A book can number its notes again from 1 in each volume.
- **What's left:** the notes are taken out of the text, and each `Section` records which
  notes its marks refer to.

## 6. EPUB (`epub/`)

`write_epub` writes an EPUB 3 that older readers can still open: it also has an NCX
table of contents. The spine is in this order:

1. **Cover**, if there is one: the PDF's first page when a picture covers at least 60%
   of it and it has at most 20 words, else the `--cover` image.
2. **Title page:** the title and author.
3. **Contents:** a nested list of parts and chapters, shown as a page of the book.
4. **One page per section**, so every chapter starts on a new page. A part with no text
   of its own is a division page with an ornament (⁂).
5. **Notes page**, if the book has notes. Marks link to it (`epub:type="noteref"`),
   and each note links back to its first mark.

All pages share one stylesheet (`epub/style.py`). It sets large centred headings and
verse set in from the text, with a hanging indent for wrapped lines. Text is justified
and hyphenated, except in Georgian books: readers rarely hyphenate Georgian, and its
long words open wide gaps in justified lines, so it is set ragged-right. The fonts are
embedded so every reader shows the same type.
