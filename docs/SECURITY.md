# Security

## What is supported

The latest release. Older releases get no fixes.

## Reporting a problem

Please don't open a public issue. Email andria24b@gmail.com with "Security" in the
subject, saying:

- what the problem is, and where (the file and line, if you know)
- how to make it happen: a PDF that does it, or how to make one
- what someone could do with it

You'll get an answer within a week. Once it's fixed, you'll be credited in the release
notes if you'd like to be.

## What counts

PDF2EPUB reads PDFs from anyone, so a PDF that makes it do harm counts: writing outside
the EPUB, putting markup or scripts from the PDF into the EPUB unescaped, or running for
hours or taking all the memory on a small file.

Problems in PyMuPDF, which reads the PDFs, go to
[PyMuPDF](https://github.com/pymupdf/PyMuPDF/security) instead.
