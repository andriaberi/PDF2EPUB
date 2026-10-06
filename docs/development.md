# Development

## Setup

```sh
git clone https://github.com/andriaberi/Bookflow
cd Bookflow
make install
```

`make install` creates `.venv`, installs Bookflow in editable mode with its dev tools
(ruff, mypy, pytest, pre-commit), and installs the git hooks. Run `make` alone for the
full list of commands.

| Command | What it does |
|---|---|
| `make check` | Lint, type-check and test: what CI runs. Run it before every commit. |
| `make format` | Format the code and fix what can be fixed. |
| `make test` / `make cov` | Run the tests, without or with a coverage report. |
| `make bump TO=patch\|minor\|major\|1.2.3` | Set the version in `src/bookflow/__init__.py`. |
| `make build` | Build the package into `dist/`. |

Run the converter from the clone with `.venv/bin/bookflow book.pdf`, or
`.venv/bin/bookflow` alone for the window. On Linux the dev setup needs a web view for
the window: `.venv/bin/pip install -e ".[qt]"` (see the README).

## Layout

```
src/bookflow/
  __main__.py      entry point: the window without arguments, the CLI with a PDF
  cli/             command-line options (Args)
  gui/             the window (pywebview): window.py opens it, api.py is what the
                   page can call, form.py checks the fields, web/ is the page itself
  pipeline.py      runs the stages (convert) and reports the result
  labels.py        division words: ტომი, ნაწილი, წიგნი, თავი, Volume, Part, ...
  pdf/             PDF → pages of clean lines (reader, spacing, text, noise, language)
  paragraphs/      lines → paragraphs (layout rules, verse)
  structure/       paragraphs → sections (headings, front matter, printed contents,
                   notes)
  cover/           cover from the PDF or an image file
  epub/            sections → EPUB 3 (pages, contents, style, fonts)
tests/             one folder per package, plus test_pipeline.py
```

`pipeline.convert` runs a conversion and returns a `Result` or raises `ConvertError`; it
reports each step to a `progress` callback. The CLI (`run`) prints the result; the
window runs `convert` in a background thread and sends each step to the page.

The window is plain HTML, CSS and JavaScript in `gui/web/`, with no build step. The page
calls Python through `window.pywebview.api` (the public methods of `Api`), and Python
calls back into `window.bookflow` (`onPicked`, `onProgress`, `onDone`, `onError`).
Keep everything Python does in `Api`, so it is tested without a window; open
`web/index.html` in a browser with a stand-in `window.pywebview.api` to work on the
design.

Each package only uses the ones before it in the pipeline:
`pdf` ← `paragraphs` ← `structure` ← `epub`. `labels.py` sits outside them all because
both `paragraphs` (verse must not swallow a heading) and `structure` need the label words.

[How it works](how-it-works.md) describes every stage and its rules.

## Conventions

- **Thresholds are named constants** at the top of their module, with a comment saying
  what they mean and why. Measure in line heights, not points, so a rule works at any
  font size.
- **Rules come from real books.** When a book converts badly, find the page and look at
  the line positions, then write the rule. Add a test with a small hand-built page that
  shows the case. The tests in `tests/paragraphs` and `tests/structure` build `Line`s
  with exact positions for this.
- **Check other books for regressions.** Before and after a change to detection, compare
  the heading list and the paragraph count on several real books. A change that fixes one
  book should not move the others unless that's an improvement too.
- **Commits** have a short imperative subject and no body ("Keep the line breaks of
  verse and lists"). A larger change is split into commits in the order it was built,
  each passing `make check`. A release is its own commit: "Version update to 1.2.0".

## Common changes

**A new division word** (e.g. "Section"): add it to `LABELS` in `labels.py` with its
level. Label words must be lower case. Add cases to `test_label_level` in
`tests/structure/test_structure.py`.

**A new section name** (e.g. "Interlude"): add it to `SECTION_NAMES` in `labels.py`, in
lower case.

**A new notes or contents title**: add it to `TITLES` in `structure/notes.py` or
`structure/contents.py`, in lower case.

**A new language**:
1. Map its script to a language code in `SCRIPT_LANGUAGES` (`pdf/language.py`).
2. Add its division words to `labels.py`.
3. Add the contents and notes page titles to `CONTENTS` and `NOTES` in
   `epub/navigation.py`.
4. If the language uses a new script, it may also need a font in `epub/fonts/`,
   listed in `FONTS` (`epub/writer.py`) and in `@font-face` in `epub/style.py`.

**Looking at a page**: print a page's lines with their positions to see why a rule
fires or doesn't:

```python
from bookflow.pdf import read_pdf

book = read_pdf("book.pdf", "157")
for line in book.pages[0].lines:
    print(round(line.x0), round(line.x1), round(line.y0), line.text)
```

A single page has no book column to compare against. To see what the paragraph stage
does with a page, read the whole book, or at least a few dozen pages around it.
