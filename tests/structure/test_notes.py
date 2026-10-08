from pdf2epub.paragraphs import Paragraph
from pdf2epub.structure import Heading, Section, extract_notes


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


def test_notes_without_a_title_are_known_by_their_numbers() -> None:
    chapter = section("tesoro,[1] coterie[2] და bébé.[3]", "[1] (იტალ.) ჩემო საუნჯევ.")
    chapter.paragraphs += [Paragraph("[2] (ფრანგ.) პარტია.", 1), Paragraph("[3] ბავშვი.", 1)]
    notes = extract_notes([chapter])
    assert [note.text for note in notes] == ["(იტალ.) ჩემო საუნჯევ.", "(ფრანგ.) პარტია.", "ბავშვი."]
    assert [p.text for p in chapter.paragraphs] == ["tesoro,[1] coterie[2] და bébé.[3]"]


def test_a_few_numbered_paragraphs_are_not_notes() -> None:
    chapter = section("ტექსტი.", "[1] პირველი.", "[3] მესამე.", "[4] მეოთხე.")
    assert extract_notes([chapter]) == []


def keyed(*notes: str) -> list[str]:
    return ["შენიშვნები", "წითელი და შავი", *notes]


def test_starred_words_link_to_notes_keyed_by_page() -> None:
    chapter = section(
        "ქალაქი ფრანშკონტეში.* ჰელვეციის* მთები.",
        *keyed("გვ. 45. ფრანშკონტე _ პროვინცია.", "გვ. 46. ჰელვეცია _ შვეიცარია."),
    )
    notes = extract_notes([chapter])
    assert [(note.mark, note.text) for note in notes] == [
        ("1", "ფრანშკონტე _ პროვინცია."),
        ("2", "ჰელვეცია _ შვეიცარია."),
    ]
    assert [p.text for p in chapter.paragraphs] == ["ქალაქი ფრანშკონტეში.[1] ჰელვეციის[2] მთები."]
    assert chapter.notes == {"1": notes[0], "2": notes[1]}


def test_keyed_note_printed_line_by_line_is_joined() -> None:
    chapter = section(
        "«საიდუმლო ნოტა»* დაიწერა.",
        *keyed("გვ. 449. «საიდუმლო ნოტა» _ აღწერილია", "მოვლენები.", "გვ. 458. პიტტი _ მტერი."),
    )
    notes = extract_notes([chapter])
    assert [note.text for note in notes] == [
        "«საიდუმლო ნოტა» _ აღწერილია მოვლენები.",
        "პიტტი _ მტერი.",
    ]


def test_star_marks_the_word_before_a_numeral() -> None:
    chapter = section(
        "ანრი III-ისა* და დ’ობინიეს.*", *keyed("გვ. 302. ანრი III _ მეფე.", "დ’ობინიე _ მწერალი.")
    )
    extract_notes([chapter])
    assert chapter.paragraphs[0].text == "ანრი III-ისა[1] და დ’ობინიეს.[2]"


def test_the_starred_word_counts_before_the_one_ahead_of_it() -> None:
    chapter = section(
        "წმ. ავგუსტინეს, წმ. ბონავენტურას,* წმ. ბასილის*",
        *keyed(
            "გვ. 210. წმ. ავგუსტინე, წმ. ბასილი _ ეკლესიის მამები.", "ბონავენტურა _ ფილოსოფოსი."
        ),
    )
    extract_notes([chapter])
    # Marks are numbered in the notes' order.
    assert chapter.paragraphs[0].text == "წმ. ავგუსტინეს, წმ. ბონავენტურას,[2] წმ. ბასილის[1]"


def test_star_matching_no_term_takes_the_note_between_its_neighbours() -> None:
    chapter = section(
        "ფლერი,* რევოლუციონერებს დანაშაულით?* მიქელანჯელო.*",
        *keyed(
            "გვ. 1. ფლერი _ მოძღვარი.",
            "გვ. 2. ესპანეთის რევოლუცია _ აჯანყება.",
            "მიქელანჯელო _ მხატვარი.",
        ),
    )
    notes = extract_notes([chapter])
    assert chapter.notes["2"] is notes[1]


def test_star_far_from_its_note_still_finds_it() -> None:
    chapter = section(
        "პრეფექტი ჩამოვიდა. ფლერი,* მიქელანჯელო,* რაფაელი,* ტიციანი,* რემბრანდტი.*",
        "მერე პრეფექტი* წავიდა.",
        *keyed(
            "გვ. 1. პრეფექტი _ ადმინისტრატორი.",
            "ფლერი _ მოძღვარი.",
            "მიქელანჯელო _ მხატვარი.",
            "რაფაელი _ მხატვარი.",
            "ტიციანი _ მხატვარი.",
            "რემბრანდტი _ მხატვარი.",
        ),
    )
    notes = extract_notes([chapter])
    assert chapter.paragraphs[1].text == "მერე პრეფექტი[1] წავიდა."
    assert chapter.notes["1"] is notes[0]
