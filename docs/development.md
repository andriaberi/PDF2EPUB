# Development

```sh
git clone https://github.com/andriaberi/Rebind
cd Rebind
make install
```

| Command | What it does |
|---|---|
| `make check` | Lint, type-check and test, as CI does. |
| `make format` | Format the code and fix what ruff can. |
| `make test` | Run the tests. |
| `make bump VERSION=1.2.3` | Set the version. |
| `make build` | Build the package into `dist/`. |

Run the converter with `.venv/bin/rebind book.pdf`, or `.venv/bin/rebind` for the
window. On Linux the window needs a web view: `.venv/bin/pip install -e ".[qt]"`.

## Layout

```
src/rebind/
  pipeline.py   runs the stages and reports the result
  labels.py     division words: ტომი, ნაწილი, წიგნი, თავი, Volume, Part, ...
  pdf/          PDF → pages of clean lines
  paragraphs/   lines → paragraphs and verse
  structure/    paragraphs → sections, front matter, printed contents, notes
  cover/        cover from the PDF or an image file
  epub/         sections → EPUB 3
  cli/          command-line options
  gui/          the window: api.py is what the page calls, web/ is the page
```

Each package uses only the ones before it: `pdf` ← `paragraphs` ← `structure` ← `epub`.
`labels.py` sits outside them because `paragraphs` and `structure` both need it.

The window's page calls Python through `window.pywebview.api` (the public methods of
`Api`), and Python calls back into `window.rebind`. Keep the logic in `Api` so it is
tested without a window.

## Conventions

- Thresholds are named constants at the top of their module. Measure in line heights,
  not points, so a rule works at any font size.
- Rules come from real books. When a book converts badly, look at the page's line
  positions, write the rule, and add a test with a small hand-built page.
- Before and after a change to detection, compare the headings and paragraph count on
  several real books.
- After changing what `epub/` writes, check a book with
  [epubcheck](https://github.com/w3c/epubcheck/releases): it should report no errors
  or warnings.
- Commits have a short imperative subject and no body.
