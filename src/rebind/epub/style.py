# One stylesheet for every page. Nothing relies on pseudo-elements or colour, which
# many readers ignore.
STYLESHEET = """\
@charset "utf-8";

/* Embedded so every reader shows the same type. Noto Serif carries Latin,
   digits and punctuation; Noto Serif Georgian carries the Georgian letters. */
@font-face {
  font-family: "Rebind Serif";
  font-style: normal;
  font-weight: normal;
  src: url(fonts/NotoSerif-Regular.ttf);
}
@font-face {
  font-family: "Rebind Serif";
  font-style: normal;
  font-weight: bold;
  src: url(fonts/NotoSerif-Bold.ttf);
}
@font-face {
  font-family: "Rebind Serif";
  font-style: italic;
  font-weight: normal;
  src: url(fonts/NotoSerif-Italic.ttf);
}
@font-face {
  font-family: "Rebind Georgian";
  font-style: normal;
  font-weight: normal;
  src: url(fonts/NotoSerifGeorgian-Regular.ttf);
}
@font-face {
  font-family: "Rebind Georgian";
  font-style: normal;
  font-weight: bold;
  src: url(fonts/NotoSerifGeorgian-Bold.ttf);
}

/* A little larger than readers' default, about 17.6px rather than 16px. */
body {
  margin: 0 5%;
  font-family: "Rebind Serif", "Rebind Georgian", serif;
  font-size: 1.1em;
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

/* Verse and lists keep their lines, set in from the text, stanzas apart. A line
   too long for the screen wraps under itself, indented, so it still reads as one. */
div.verse {
  margin: 0.8em 0 0.8em 1.5em;
}

div.verse p {
  padding-left: 1.5em;
  text-align: left;
  text-indent: -1.5em;
  -webkit-hyphens: none;
  -epub-hyphens: none;
  hyphens: none;
}

/* Headings: big, bold, centred, never hyphenated or left alone at a page end.
   Sizes go by role, not by tag, so a chapter looks the same whether the book
   has chapters only (h1) or parts, books and chapters (h3). */
h1,
h2,
h3 {
  margin: 3.5em 0 2em;
  font-size: 1.6em;
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

/* The outermost division, a volume where the book has them, is the largest. */
.division h1 {
  font-size: 2.4em;
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

/* A scene break inside a chapter, as the book prints it: "*", "* * *". */
.scene-break {
  margin: 1em 0;
  text-align: center;
  text-indent: 0;
}

/* Cover: the picture alone, filling the screen. */

body.cover {
  margin: 0;
  padding: 0;
  text-align: center;
}

section.cover {
  height: 100vh;
  margin: 0;
  padding: 0;
}

section.cover svg {
  width: 100%;
  height: 100%;
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
  margin: 1.5em 0 1.5em;
}

nav ol {
  margin: 0;
  padding: 0;
  list-style: none;
}

/* Wrapped titles line up under the first line's text, not under the label. */
nav li {
  margin: 0.4em 0;
  padding-left: 1.2em;
  text-align: left;
  text-indent: -1.2em;
  -epub-hyphens: none;
  hyphens: none;
}

/* "თავი მეოცე:" never breaks between its words. */
nav .label {
  white-space: nowrap;
}

/* Chapters sit under their part or volume. */
nav li li {
  margin-left: 0.6em;
}

nav .group {
  margin-top: 1.2em;
}

nav .group > a {
  font-weight: bold;
}

nav > ol > .group {
  margin-top: 1.8em;
}

nav > ol > .group:first-child {
  margin-top: 0;
}

nav > ol > .group > a {
  font-size: 1.15em;
}

nav a {
  color: inherit;
  text-decoration: none;
}

/* Notes: small raised marks in the text, a plain list at the end. */

a.noteref {
  font-size: 0.7em;
  line-height: 0;
  vertical-align: super;
  text-decoration: none;
}

.notes h1 {
  margin: 1.5em 0 1.5em;
}

.notes ol {
  margin: 0;
  padding: 0;
  list-style: none;
}

.notes li {
  margin: 0 0 0.6em;
}

.notes p {
  text-indent: 0;
}

.notes .mark {
  font-weight: bold;
}

.notes .mark a {
  color: inherit;
  text-decoration: none;
}
"""
