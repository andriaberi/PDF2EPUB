import pdf2epub


def test_has_a_version() -> None:
    assert isinstance(pdf2epub.__version__, str)
    assert pdf2epub.__version__
