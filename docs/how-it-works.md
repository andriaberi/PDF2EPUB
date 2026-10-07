# How Rebind works

`pipeline.py` runs these stages in order. Each takes the previous one's output:

```
PDF → pdf/ → structure/contents.py → paragraphs/ → structure/ → structure/notes.py → epub/
```

Most rules compare a line with the book's usual **text column**: the median margins,
line height and gap of pages with at least ten lines. Distances are measured in line
heights, so the rules work at any font size. The exact thresholds are named constants
at the top of each module.

## 1. Reading the PDF (`pdf/`)

`read_pdf` returns a `Book` of `Page`s, each a list of `Line`s with text and position.

- **Lines:** pieces of one printed line are joined left to right.
- **Missing spaces:** when a PDF has almost no space characters, word breaks are found
  from where each letter starts. Inside a word a letter always moves the next by its
  own width, so a larger step starts a new word.
- **Text:** Unicode NFC, ligatures spelled out, invisible characters removed, OCR dash
  runs ("–-") made one em dash, and a letter-spaced heading line ("IV წ ი გ ნ ი") joined.
- **Noise:** page numbers, running headers and footers (edge lines repeating on several
  pages), and footnote blocks at the foot of a page are removed. A chapter label at a
  page edge is a header only if it is on two pages in a row. Only scanned pages (an
  image covering half the page) lose OCR junk lines and edge specks; on a born-digital
  page an odd line is the book's own text.
- **Language:** the PDF's `/Lang`, else the main script (Georgian → `ka`, Latin → `en`).
  When `/Lang` and the script disagree on whether the book is Georgian, the script wins:
  PDFs made on an English system often tag Georgian books `en-US`.

## 2. Printed contents (`structure/contents.py`)

Pages that are mostly entries ("თავი მესამე ..... 45", or a label alone) are dropped
before paragraphs are built, so they don't turn into fake headings.

## 3. Paragraphs (`paragraphs/`)

Rebind first learns how the book marks paragraphs (`layout.text_column`): by indent, by
extra space between lines, or neither. It also learns whether lines are justified, and
whether the book has stray space mid-sentence, as Word exports with hard line breaks do.

A line then starts a new paragraph when it is indented, set below a gap or a paragraph's
space, follows a short line ending a sentence, follows a heading line, or is a scene
break or a tall line. In a book of numbered sections, a line opening with the next
section's number ("29. ") after a finished sentence starts one too. A line never starts
one after a word broken at the line end, which is rejoined, or after a quote opened at
the line end. Nor does a short line between an unfinished sentence and a line opening
with closing punctuation: some books set a foreign word on a line of its own mid-
sentence. A page that is mostly dialogue or verse would mistake its indent for its
margin, so it uses the book's column instead.

A paragraph that starts well below a finished sentence is marked `apart`: it may be a
heading set in the text. Such a heading runs straight into the text below it, with no
space, and its last line stops well short of the margin.

**Verse** (`verse.py`): a run of at least four short lines, or two after a line ending
with a colon or a short line ending with a comma, where at most half end a sentence and
at most a third are speech, keeps its line breaks. A sentence of three words or more
after a line that already ended one is narration, not part of the verse. A wider gap
than the verse's own starts a new stanza.

## 4. Structure (`structure/`)

`build_sections` splits paragraphs into `Section`s at headings:

- **Labels:** a division word and a number on a line of their own, in any position but
  as a full line of text: ტომი/Volume, ნაწილი/Part, წიგნი/Book, თავი/Chapter
  (`labels.py`). One misread letter is fixed. The number may come first ("მესამე
  ნაწილი").
- **Label and title on one line:** "თავი მეშვიდე გასეირნება სანაპიროზე".
- **Chapter numbers alone** ("XII", "7."), when there are at least three, counting up.
- **Named sections:** წინათქმა, ეპილოგი, Preface, Epilogue, ... at the book's outermost
  level.
- **Headings set in the text:** short `apart` paragraphs that run straight into the text.

The short centred, flush-right or capitalised paragraphs after a label are its
**title**. Levels are renumbered from 1, and the label word is put in the same place
throughout.

**Front matter** (`front.py`): the book's title page, its reprints before later
volumes, and text before the first heading are dropped, unless that text is over a
tenth of the book. Metadata in Latin letters is replaced by the title page's Georgian
spelling when they match.

## 5. Notes (`structure/notes.py`)

A paragraph reading შენიშვნები or Notes followed by `[1] ...` paragraphs, or three
paragraphs in a row numbered `[1]`, `[2]`, `[3]`, is a block of notes. It is taken out
of the text, and the `[n]` marks before it link to it. Numbering may restart after
each block.

## 6. EPUB (`epub/`)

`write_epub` writes an EPUB 3 with an NCX for older readers. The spine has the cover
(if any), a title page, the contents, one page per section, then the notes page. A part
with no text of its own gets a division page. One stylesheet sets every page, and the
Noto Serif fonts are embedded. Georgian is set ragged-right because readers rarely
hyphenate it.
