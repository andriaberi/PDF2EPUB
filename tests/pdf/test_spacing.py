from bookflow.pdf.spacing import Glyph, lacks_spaces, learn_advances, spaced_text

# Two letters, each 0.6 of the font size wide; a word break adds 0.3 more.
WIDTH, SPACE, SIZE = 6.0, 3.0, 10.0


def set_line(*words: str) -> list[Glyph]:
    """Glyphs placed as a PDF without spaces places them: words apart by position only."""
    glyphs, x = [], 0.0
    for word in words:
        for char in word:
            glyphs.append(Glyph(char, x, SIZE, "Serif"))
            x += WIDTH
        x += SPACE
    return glyphs


LINES = [set_line("ab", "ba", "aab", "bba") for _ in range(10)]


def test_text_without_spaces_lacks_them() -> None:
    assert lacks_spaces(["ამწიგნშიჰანსკასტორპისთავგადასავალი", "გვინდაგიამბოთ"])
    assert not lacks_spaces(["ამ წიგნში ჰანს კასტორპის თავგადასავალი", "გვინდა გიამბოთ"])
    assert not lacks_spaces([])


def test_learns_each_letters_width() -> None:
    assert learn_advances(LINES) == {("Serif", "a"): 0.6, ("Serif", "b"): 0.6}


def test_puts_spaces_back_between_words() -> None:
    advances = learn_advances(LINES)
    assert spaced_text(set_line("ab", "ba", "aab"), advances) == "ab ba aab"


def test_keeps_spaces_the_pdf_has() -> None:
    advances = learn_advances(LINES)
    assert spaced_text(set_line("ab ", "ba"), advances) == "ab ba"


def test_letter_after_a_comma_starts_a_word() -> None:
    glyphs = [Glyph(c, 6.0 * i, SIZE, "Serif") for i, c in enumerate("ab,ba")]
    assert spaced_text(glyphs, learn_advances(LINES)) == "ab, ba"
