# One stylesheet for every page, so the whole book is set the same way.
#
# Clean and conservative, after the reference converter: sizes, weight and
# centring sit on the heading elements themselves, and nothing relies on
# pseudo-elements or colour, which many readers ignore.
STYLESHEET = """\
@charset "utf-8";

body {
  margin: 0 5%;
  font-family: serif;
  line-height: 1.5;
  text-align: justify;
  -webkit-hyphens: auto;
  -epub-hyphens: auto;
  hyphens: auto;
  widows: 2;
  orphans: 2;
}

/* Readers rarely hyphenate Georgian, and its words are long, so justified lines
   open wide gaps. A ragged right edge reads more evenly. */
html:lang(ka) body {
  text-align: left;
}

section {
  margin: 0;
  padding: 0;
}

p {
  margin: 0;
  text-indent: 1.5em;
}

/* Headings: big, bold, centred, never hyphenated or left alone at a page end. */

h1,
h2,
h3 {
  font-weight: bold;
  line-height: 1.25;
  text-align: center;
  text-indent: 0;
  -webkit-hyphens: none;
  -epub-hyphens: none;
  hyphens: none;
  page-break-after: avoid;
  break-after: avoid;
  page-break-inside: avoid;
  break-inside: avoid;
}

/* Sizes go by role, not by tag, so a chapter looks the same whether the book
   has chapters only (h1) or parts, books and chapters (h3). */

h1,
h2,
h3 {
  font-size: 1.6em;
  margin: 3.5em 0 2em;
}

/* "თავი პირველი" above the title: smaller, plain, spaced out. */
h1 .label,
h2 .label,
h3 .label {
  display: block;
  margin-bottom: 0.7em;
  font-size: 0.55em;
  font-weight: normal;
  letter-spacing: 0.15em;
}

/* The first paragraph after a heading starts flush, as in print. */
h1 + p,
h2 + p,
h3 + p {
  text-indent: 0;
}

/* A part or book that only holds chapters: a page of its own, set lower, larger. */
.division h1,
.division h2,
.division h3 {
  margin: 30% 0 0;
  font-size: 2em;
}

.division h1 .label,
.division h2 .label,
.division h3 .label {
  font-size: 0.45em;
}

.ornament {
  margin: 1em 0 0;
  text-align: center;
  text-indent: 0;
}

/* Title page */

.titlepage {
  text-align: center;
}

.titlepage h1 {
  margin: 30% 0 0.8em;
  font-size: 2em;
}

.titlepage .author {
  text-align: center;
  text-indent: 0;
  font-size: 1.2em;
}

/* Contents */

nav h1 {
  margin: 1.5em 0 1.2em;
}

nav ol {
  margin: 0 0 0 1.2em;
  padding: 0;
  list-style: none;
}

nav > ol {
  margin-left: 0;
}

nav li {
  margin: 0.35em 0;
  text-align: left;
  text-indent: 0;
}

nav > ol > li {
  margin-top: 0.9em;
}

nav > ol > li > a {
  font-weight: bold;
}

nav a {
  color: inherit;
  text-decoration: none;
}
"""
