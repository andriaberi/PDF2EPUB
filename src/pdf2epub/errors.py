class ConvertError(Exception):
    """The book can't be converted: a bad PDF, page range or cover, or nowhere to write."""


class BookError(ConvertError):
    """The book's data can't be used."""
