from bookflow.paragraphs import Paragraph
from bookflow.structure import Heading, Section, extract_notes


def section(*texts: str) -> Section:
    return Section(Heading(1, "თავი პირველი"), [Paragraph(text, 1) for text in texts])


def test_notes_are_taken_out_and_linked() -> None:
    chapter = section(
        "ფრეილინა[1] და ლივრეა[2].",
        "შენიშვნები",
        "[1] ფრეილინა – მხლებელი. [2] ლივრეა – ტანსაცმელი.",
    )
    notes = extract_notes([chapter])
    assert [(note.mark, note.text) for note in notes] == [
        ("1", "ფრეილინა – მხლებელი."),
        ("2", "ლივრეა – ტანსაცმელი."),
    ]
    assert [p.text for p in chapter.paragraphs] == ["ფრეილინა[1] და ლივრეა[2]."]
    assert chapter.notes == {"1": notes[0], "2": notes[1]}


def test_note_going_on_in_another_paragraph_stays_whole() -> None:
    chapter = section("სიტყვა[1].", "შენიშვნები", "[1] ერთი", "(გაგრძელება)", "[2] ორი")
    notes = extract_notes([chapter])
    assert [note.text for note in notes] == ["ერთი (გაგრძელება)", "ორი"]


def test_stray_digit_after_the_mark_is_dropped() -> None:
    [note] = extract_notes([section("ლექსი[24].", "შენიშვნები", "[24]1 საამო ღამეს")])
    assert (note.mark, note.text) == ("24", "საამო ღამეს")


def test_each_volume_links_to_its_own_notes() -> None:
    first = section("ერთი[1].", "შენიშვნები", "[1] პირველი ტომის.")
    second = section("ორი[1].", "შენიშვნები", "[1] მეორე ტომის.")
    notes = extract_notes([first, second])
    assert first.notes["1"].text == "პირველი ტომის."
    assert second.notes["1"].text == "მეორე ტომის."
    assert len({note.id for note in notes}) == 2


def test_marks_without_a_notes_title_stay_text() -> None:
    chapter = section("[1] ტექსტი, არა შენიშვნა.")
    assert extract_notes([chapter]) == []
    assert chapter.paragraphs[0].text == "[1] ტექსტი, არა შენიშვნა."
