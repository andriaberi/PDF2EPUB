# How Rebind works

Rebind turns a PDF into an EPUB in stages. Each stage takes the previous one's
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
- **Missing spaces** (`spacing.py`). Some PDFs place every word where it belongs but
  leave out the spaces, and their font widths are wrong, so no gap shows between the
  letters either. When less than 5% of a book's characters are spaces (text normally
  has about 14%), Rebind reads each letter's position instead:
  - Inside a word a letter always moves the next one along by the same amount, its
    width. The most common distance after each letter in the book is that width.
  - Where a letter moves the next one more than 0.15 font sizes further than its width,
    a new word starts. A real space is about 0.25.
  - A letter right after a comma, full stop or other closing punctuation starts a new
    word too.
- **Text cleaning** (`text.py`) is done line by line:
  - Unicode NFC, with ligatures (`ﬁ`) spelled out and invisible characters removed.
  - Runs of dashes that OCR made from one ("–-") become one em dash.
  - A word broken at the line end keeps a plain `-`, so the paragraph stage can rejoin it.
  - Stray middle dots become spaces.
- **Noise** (`noise.py`) is removed page by page:
  - **Junk lines:** OCR misreads of pictures and stains, meaning lines with no real word,
    or with more broken words than real ones. Only **scanned pages** are cleaned this
    way: pages that an image covers at least half of, with the OCR text on top. On a
    born-digital page an odd line ("#34", "A", "Lise-მაც ამოიოხრა.") is the book's own
    text, so it stays, and so do symbols at a line's edges.
  - **Page numbers:** short lines with no word, in the top or bottom 12% of the page.
  - **Running headers and footers:** edge lines whose words repeat on 3 or more pages.
    Digits are ignored, so "Chapter 3 · 41" and "Chapter 3 · 42" match. A chapter
    label at the top or foot of a page repeats too, since every book of a novel has
    its "თავი მესამე", so a label counts as a header only when it is on the edge of
    two pages in a row.
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

Books mark paragraphs in different ways, so before building them Rebind learns four
things about the whole book (`text_column`), from its pages with at least ten lines:

- **Spaced paragraphs.** Some books leave out the indent and put a little space above
  each paragraph instead. A step from one line to the next of 1.2 to 2.5 times the usual
  one is a wide step. When at least 2% of steps are wide and at least 90% of those
  follow the end of a sentence (or a note mark), the book spaces its paragraphs. The
  paragraph step is then halfway between the usual step and the usual wide one.
- **Loose spacing.** When wide steps are that common but fewer than 90% follow a sentence
  end, the space means nothing. A Word export with a hard break every few lines puts
  the paragraph space after each of them, mid-sentence too.
- **Indents.** The book indents its paragraphs if at least 3% of lines start between
  0.8 and 4 line heights inside the margin.
- **Justified text.** In justified text a line stops within half a line height of the
  right margin, or well short of it as a paragraph's last line. The book is justified
  if at least 60% of its lines are flush and at most 5% stop in between.

A line **starts a new paragraph** if any of these is true. The first rule that applies
wins:

1. The line above ends in a broken word, or is a dialogue dash alone ("-"): **never a
   new paragraph**. Neither is a line opening with closing punctuation (`.` `,` `!` `?`
   `;` `:` `)` `»`), which ends the sentence above: "Est modus in rebus" / ". დიახ".
2. Either this line or the one above is a scene break: only `*`, `⁂`, `•` and the like,
   or a row of three dashes or more.
3. Either this line or the one above is tall (more than 1.3× the usual height): a heading.
   So is a chapter number alone on its line, "XII" or "7.".
4. The line above is a short line reading as a heading: a label ("თავი მეორე"), a label
   with its title, or a section name ("წინათქმა"). Some books leave no gap after one.
5. The line above starts more than 4 line heights to the right of this one. It was
   centred or flush right, like a heading.
6. The line is indented by more than 0.8 line heights.
7. There is a gap above it wider than the usual gap plus 0.8 line heights. In a loosely
   spaced book a long line (over 60% of the column) running on mid-sentence carries
   on across the gap, unless this line opens speech or a quote.
8. In a book that spaces its paragraphs, the step from the line above is at least the
   paragraph step, and the line above ends a sentence or this line opens speech or a
   quote. A sentence running on across the space carries on.
9. It is the first line of a page, and the last page's text stopped above 75% of the
   page height (a chapter end).
10. A heading set in the text ends (see below).
11. The line above ends a sentence and stops more than 2 line heights short of the
    right edge, or more than half a line height in justified text.

Words broken at a line end are rejoined ("დარჩე-" + "ნია" → "დარჩენია").

### Headings set in the text

Some books set a section's name between paragraphs, with no label and in the text's
size: "რესტორანში", "#34". A paragraph that may be such a heading is marked `apart`:

- **With space:** it starts after a finished sentence, more than 1.8 times the usual
  step below it (1.8 paragraph steps in a book that spaces paragraphs). The heading
  ends at its short last line, at most 3 lines in, when a full line follows. Short
  lines close below it go on the heading: "გაალმასება." / "და კიდევ ერთი … რამ".
- **Without space,** in a book with no indents: a line of at most 6 words and less than
  60% of the column, flush left, after a finished sentence and before a full line, that
  ends with no punctuation and has none inside ("ჰიპე"). A line with a foreign word
  glued on ("…სხვაHybris") is the text's own, and so is a line before a bracketed
  translation, unless its Latin letters are capitals: a heading and its translation,
  "OPERATIONES SPIRITUALES" / "(სულიერი წვრთნა (ლათ.).)".

The structure stage decides which of these are headings.

### Verse and lists (`paragraphs/verse.py`)

Songs, poems, lists and inscriptions lose their sense when their lines run together,
so they become **verse paragraphs**. These keep each line as printed. A run of lines
on a page is verse if:

- **It has at least 4 lines,** or at least 2 right after a line ending with a colon
  ("…და სიმღერა დაიწყო:"). Each line is:
  - stopping more than 4 line heights short of the right edge,
  - not opening with closing punctuation (`.` `,` `!` `?` `;` `)` `»`),
  - not tall, and
  - not a chapter label.
- **At most half of its own lines end a sentence** (`.`, `!`, `?`, `…`, before any
  closing quote). Short lines that each end a sentence are short paragraphs of text,
  such as quick dialogue or narration.
- **At most a third of its lines are speech,** opening with a dialogue dash (`-`, `–`,
  `—`): a song may have a dialogue in it ("- ტილო გარეცხე!" / "- სად გავრეცხო?"). Speech
  doesn't count towards the sentence ends. A run that fails with its speech may still
  have verse in the parts between the speech.

Text around the verse is trimmed off first:
- from its start: speech, the last line of the paragraph above (no indent, no gap
  before it), and short lines ending a sentence or with a colon ("…ლექსი დაუწერა:");
- from its end: speech and lines ending with a colon, the narration after a song
  ("- საწყალი ცხენი, - ამოიოხრა ფანტინმა." / "დალიამ იუცხოვა ეს სიბრალული:").

**Stanzas** are split where the gap between two verse lines is wider than the verse's
own usual gap plus 0.8 line heights. The verse's own gap matters because some books
space verse wider than prose.

## 4. Structure (`structure/`)

`build_sections` splits the paragraphs into `Section`s, each a `Heading` and the
paragraphs up to the next one. Text before the first heading is front matter.

### Labels

A **label** is a division word plus one number word, alone on its line
(`rebind/labels.py`):

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

### Label and title on one line

Some books print the title on the label's line: "თავი მეშვიდე გასეირნება სანაპიროზე",
"თავი მეექვსე - FONTIS". Such a line is a heading if it is short, starts with a label
word spelled exactly, then a number (a numeral, a Georgian ordinal such as მეშვიდე, or
an English number word), and doesn't end a sentence. A dash between label and title is
dropped. A label followed by a dash alone takes its title from the next line.

### Named sections

A section name alone on a short line is a heading without a number: წინათქმა,
წინასიტყვაობა, შესავალი, პროლოგი, ეპილოგი, ბოლოთქმა, Foreword, Preface, Introduction,
Prologue, Epilogue, Afterword. It takes the outermost level the book uses, so a
foreword stands beside the parts, or beside the chapters in a book without parts.

### Numbered chapters

A chapter number alone on its line, "XII" or "7." (Roman numerals in capitals only),
is a chapter heading below every labelled division, if:

- the book has at least 3 of them, and
- each counts up from the last one by at most 2, or starts again at 1 (in a new part).

A stray "7" in the text, out of step with the numbers around it, stays as text.

### Placement

The label's line can be placed **any way except as a full line of running text**:
centred, flush left, flush right, or in a bigger font. Books differ, and only a line
that runs from the margin to the right edge rules a label out.

### Titles

The paragraphs after a label are its **title** if they:

- are at most 3 lines in all,
- are each centred or short, or written all in capitals,
- are on the same page as the label,
- don't end with a colon, which leads into speech, and
- are set off from the text after them, either by being centred or by a gap.

A label in a big font takes only a title in the same big font. The next line in text
size is the chapter's first line, and the chapter has no title.

When a title has run into the first paragraph, as across a page break, the paragraph's
short first line is split off as the title.

A **long title** may fill a line or more, set like a paragraph: "წინასწარ უნდა
ყოფილიყო ჯაჭვი განზრახ დაზიანებული, რომ ასე ადვილად / გამწყდარიყო". A paragraph right
after a label is its title if it is at most 3 lines, isn't a label, doesn't start with
speech or a quote and doesn't end like a sentence or clause, and the text below it starts
more than 1.8 times the usual step further down (1.8 paragraph steps in a book that
spaces paragraphs).

A scene break is never a title.

### Headings set in the text

A paragraph marked `apart` (see Paragraphs) is a **section below the chapters**, with
its text as its name, if:

- it is at most 3 lines and its last line is short,
- it is not verse, a scene break or a notes title (შენიშვნები),
- it doesn't end with `.` `,` `:` `;` or a dash, and doesn't start with a dash or a
  bracket (it may exclaim or ask: "დედაკაცია, რაღა თქმა უნდა!"), and
- the text below runs straight on from it, on the same page or at the top of the next.

### Front matter

- **Title page:** front matter of at most 3 paragraphs on one page, with none ending
  a sentence, is the book's own title page. It is dropped because the EPUB
  makes its own. Lines repeating the title or author are dropped too.
- **Title page reprints:** a title page printed again before a later volume is
  removed from the end of the section before it. It may name its own volume,
  "(ტომი II)" where the first said "(ტომი I)", and the first title page may have up
  to 6 lines, with an epigraph or the translators.
- **Title and author:** a Georgian book's metadata is often in Latin letters ("Leo
  Tolstoy"). When a line of the book's title page reads the same in Latin letters
  ("ლევ ტოლსტოი" → "lev tolstoi"), that line is used instead, without a volume note
  in brackets.
- **Other front matter:** what is left before the first heading (credits, an epigraph,
  a translator's note) is dropped too, unless it is more than a tenth of the book. That
  much text is the book itself, its first headings missed. A book without headings
  keeps all its text.

These rules are in `structure/front.py`.

## 5. Notes (`structure/notes.py`)

A notes section is a paragraph reading შენიშვნები, Notes or Endnotes, followed by
paragraphs starting with a mark: `[12] ფრეილინა – ...`. Without a title, at least three
paragraphs in a row starting `[1] `, `[2] `, `[3] ` are notes too.

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

All pages share one stylesheet (`epub/style.py`). It sets large centred headings,
verse set in from the text with a hanging indent for wrapped lines, and scene breaks
centred as the book prints them. Text is justified
and hyphenated, except in Georgian books: readers rarely hyphenate Georgian, and its
long words open wide gaps in justified lines, so it is set ragged-right. The fonts are
embedded so every reader shows the same type.
