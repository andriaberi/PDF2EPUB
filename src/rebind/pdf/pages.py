def parse_pages(spec: str | None, page_count: int) -> list[int]:
    """Turn a 1-based spec like "1-3,7,10-12" into sorted 0-based page indices."""
    if spec is None:
        return list(range(page_count))

    pages: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        start_text, sep, end_text = part.partition("-")
        try:
            start = int(start_text)
            end = int(end_text) if sep else start
        except ValueError:
            raise ValueError(f"invalid page range: {part!r}") from None

        if start < 1 or end < start:
            raise ValueError(f"invalid page range: {part!r}")
        if end > page_count:
            raise ValueError(f"page {end} is past the end of the PDF ({page_count} pages)")

        pages.update(range(start - 1, end))

    return sorted(pages)
