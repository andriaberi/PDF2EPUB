import pytest

from pdf2epub.pdf import Line
from pdf2epub.styles import styled_html, styled_text


def line(text: str, runs: list[tuple[str, str]] | None = None) -> Line:
    return Line(text, 0, 0, 0, 0, runs=runs or [])


def test_plain_lines_leave_the_text_as_it_is() -> None:
    assert styled_text("Plain text.", [line("Plain text.")]) == "Plain text."


def test_styled_runs_become_tags() -> None:
    runs = [("A ", ""), ("very", "i"), (" ", ""), ("good", "b"), (" ", ""), ("day", "bi")]
    styled = styled_text("A very good day", [line("A very good day", runs)])
    assert styled == "A <i>very</i> <b>good</b> <b><i>day</i></b>"


def test_style_carries_over_a_word_rejoined_across_lines() -> None:
    lines = [
        line("the cap-", [("the ", ""), ("cap-", "i")]),
        line("tain said", [("tain", "i"), (" said", "")]),
    ]
    assert styled_text("the captain said", lines) == "the <i>captain</i> said"


def test_style_runs_on_across_a_line_break() -> None:
    lines = [
        line("in War and", [("in ", ""), ("War and", "i")]),
        line("Peace too", [("Peace", "i"), (" too", "")]),
    ]
    assert styled_text("in War and Peace too", lines) == "in <i>War and Peace</i> too"


def test_a_mark_put_in_after_a_styled_word_stays_plain() -> None:
    lines = [line("the Nautilus sank", [("the ", ""), ("Nautilus", "i"), (" sank", "")])]
    assert styled_text("the Nautilus[3] sank", lines) == "the <i>Nautilus</i>[3] sank"


def test_spaces_stay_outside_the_tags() -> None:
    lines = [line("a  word ", [("a ", ""), (" word ", "i")])]
    assert styled_text("a word", lines) == "a <i>word</i>"


@pytest.mark.parametrize(
    ("text", "html"),
    [
        ("a &lt;i&gt;b&lt;/i&gt; c", "a <em>b</em> c"),
        ("&lt;b&gt;bold", "<strong>bold</strong>"),
        ("stray&lt;/i&gt; close", "stray close"),
        ("&lt;i&gt;&lt;i&gt;twice&lt;/i&gt;", "<em>twice</em>"),
        (
            "&lt;i&gt;a &lt;b&gt;b&lt;/i&gt; c&lt;/b&gt;",
            "<em>a <strong>b</strong></em><strong> c</strong>",
        ),
    ],
)
def test_tags_become_html_each_closed(text: str, html: str) -> None:
    assert styled_html(text) == html
