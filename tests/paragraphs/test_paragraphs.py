from pdf2epub.paragraphs import Paragraph, build_paragraphs
from pdf2epub.pdf import Line, Page

LEFT = 45.0
RIGHT = 385.0
INDENT = 62.0


def line(y: float, text: str, x0: float = LEFT, x1: float = RIGHT) -> Line:
    return Line(text, x0, y, x1, y + 10)


def page(number: int, *lines: Line) -> Page:
    return Page(number, 430, 590, list(lines))


def texts(pages: list[Page]) -> list[str]:
    return [paragraph.text for paragraph in build_paragraphs(pages)]


def test_joins_lines_with_spaces() -> None:
    p = page(1, line(100, "one two"), line(114, "three four"), line(128, "five.", x1=150))
    assert texts([p]) == ["one two three four five."]


def test_rejoins_hyphenated_words() -> None:
    p = page(1, line(100, "შვილი არ დარჩე-"), line(114, "ნია. როგორ", x1=150))
    assert texts([p]) == ["შვილი არ დარჩენია. როგორ"]


def test_keeps_hyphen_before_a_non_letter() -> None:
    p = page(1, line(100, "ten-"), line(114, "20 years", x1=150))
    assert texts([p]) == ["ten- 20 years"]


def test_indent_starts_a_paragraph() -> None:
    p = page(
        1,
        line(100, "First paragraph", x0=INDENT),
        line(114, "goes on here"),
        line(128, "Second paragraph", x0=INDENT),
        line(142, "goes on too"),
    )
    assert texts([p]) == ["First paragraph goes on here", "Second paragraph goes on too"]


def test_gap_starts_a_paragraph() -> None:
    p = page(1, line(60, "თავი პირველი", x0=170, x1=260), line(100, "ბატონი მირიელი"))
    assert texts([p]) == ["თავი პირველი", "ბატონი მირიელი"]


def test_line_in_a_bigger_font_stands_alone() -> None:
    p = page(
        1,
        Line("თავი მეორე", LEFT, 100, 120, 116),
        line(124, "ანა პავლოვნას სასტუმრო ოთახი"),
        line(138, "ხალხით ივსებოდა."),
    )
    assert texts([p]) == ["თავი მეორე", "ანა პავლოვნას სასტუმრო ოთახი ხალხით ივსებოდა."]


def test_short_line_ending_a_sentence_ends_the_paragraph() -> None:
    p = page(1, line(100, "It ended here.", x1=150), line(114, "A new one, indent lost."))
    assert texts([p]) == ["It ended here.", "A new one, indent lost."]


def test_continues_across_pages() -> None:
    first = page(1, line(100, "აქვე გარდაეცვალა ცოლი გუ-"))
    second = page(2, line(20, "ლის ავადმყოფობით."), line(34, "more text", x1=150))
    paragraphs = build_paragraphs([first, second])
    assert [p.text for p in paragraphs] == ["აქვე გარდაეცვალა ცოლი გულის ავადმყოფობით. more text"]
    assert paragraphs[0].page == 1


def test_new_page_after_finished_paragraph_starts_a_new_one() -> None:
    first = page(1, line(100, "Some text"), line(114, "The end.", x1=150))
    second = page(2, line(20, "Next one starts"), line(34, "here"))
    assert texts([first, second]) == ["Some text The end.", "Next one starts here"]


def test_hyphen_wins_over_indent() -> None:
    p = page(1, line(100, "მნიშვნე-"), line(114, "ლოვან მოვლენას", x0=INDENT))
    assert texts([p]) == ["მნიშვნელოვან მოვლენას"]


def test_skips_empty_pages() -> None:
    assert texts([page(1), page(2, line(100, "Text"))]) == ["Text"]


def test_page_ending_early_ends_the_paragraph() -> None:
    first = page(1, line(300, "თბილისი — 1963", x0=170, x1=260))
    second = page(2, line(300, "ფრანგულიდან თარგმნა", x0=170, x1=260))
    assert texts([first, second]) == ["თბილისი — 1963", "ფრანგულიდან თარგმნა"]


def full_page(number: int) -> Page:
    """Ordinary text, so the book's column can be measured."""
    return page(number, *(line(40 + 14 * row, "ტექსტი") for row in range(12)))


def verse_of(paragraphs: list[Paragraph]) -> list[list[str]]:
    return [[line.text for line in p.lines] for p in paragraphs if p.verse]


def test_verse_keeps_its_lines() -> None:
    p = page(
        2,
        line(100, "მერე ნიკოლაიმ იმღერა ჰანგი:", x1=200),
        line(124, "В приятну ночь, при лунном свете,", x1=200),
        line(138, "Представить счастливо себе,", x1=180),
        line(152, "Что некто есть еще на свете,", x1=190),
        line(166, "Кто думает и о тебе!", x1=150),
        line(190, "ტექსტი გრძელდება და გრძელდება"),
    )
    paragraphs = build_paragraphs([full_page(1), p])
    assert verse_of(paragraphs) == [
        [
            "В приятну ночь, при лунном свете,",
            "Представить счастливо себе,",
            "Что некто есть еще на свете,",
            "Кто думает и о тебе!",
        ]
    ]
    assert "მერე ნიკოლაიმ იმღერა ჰანგი:" in [p.text for p in paragraphs]


def test_wider_gap_parts_stanzas() -> None:
    lines = ["ერთი,", "ორი,", "სამი,", "ოთხი"]
    p = page(
        2,
        *(line(100 + 14 * row, text, x1=150) for row, text in enumerate(lines)),
        *(line(180 + 14 * row, text, x1=150) for row, text in enumerate(lines)),
    )
    assert verse_of(build_paragraphs([full_page(1), p])) == [lines, lines]


def test_short_sentences_are_not_verse() -> None:
    lines = ["მეორედ დააკაკუნა.", "ხმა შემოესმა.", "არავინაა.", "მესამედ დააკაკუნა."]
    p = page(2, *(line(100 + 14 * row, text, INDENT, 200) for row, text in enumerate(lines)))
    paragraphs = build_paragraphs([full_page(1), p])
    assert verse_of(paragraphs) == []
    assert [p.text for p in paragraphs[1:]] == lines


def test_dialogue_is_not_verse() -> None:
    lines = ["- ერთი,", "- ორი,", "- სამი,", "- ოთხი"]
    p = page(2, *(line(100 + 14 * row, text, INDENT, 150) for row, text in enumerate(lines)))
    assert verse_of(build_paragraphs([full_page(1), p])) == []


def verse_page(*texts: str, intro: str | None = None, after: str | None = None) -> Page:
    """Short indented lines, with a line of text leading in and one following."""
    lines = [line(100, intro, x1=200)] if intro else []
    lines += [line(114 + 14 * row, text, INDENT, 180) for row, text in enumerate(texts)]
    if after:
        lines.append(line(114 + 14 * len(texts), after, INDENT, RIGHT))
    return page(2, *lines)


def test_two_lines_after_a_colon_are_verse() -> None:
    p = verse_page(
        "ხელი რა ნაზია,",
        "ფეხიც ლამაზია,",
        intro="ჩამოჯდა და სიმღერა დაიწყო:",
        after="იდაყვი მუხლზე დაედო და სიმღერას ფეხის ქნევას აყოლებდა.",
    )
    assert verse_of(build_paragraphs([full_page(1), p])) == [["ხელი რა ნაზია,", "ფეხიც ლამაზია,"]]


def test_two_short_lines_without_a_colon_are_text() -> None:
    p = verse_page("ხელი რა ნაზია,", "ფეხიც ლამაზია,", intro="ჩამოჯდა და სიმღერა დაიწყო.")
    assert verse_of(build_paragraphs([full_page(1), p])) == []


def test_two_lines_after_a_short_line_ending_in_a_comma_are_verse() -> None:
    p = page(
        2,
        line(86, "მაგიდაზე წესრიგი სუფევდა და მაგიდის ქვეშ კი - უწესობა."),
        line(100, "მოლიერისა არ იყოს,", x1=200),
        line(114, "ისეთ რამეს აკეთებდნენ მაგიდის ქვეშ ფეხით,", INDENT, 180),
        line(128, "ყველაფერი ზანზარებდა, გრგვინვა იყო მეხის.", INDENT, 180),
    )
    assert verse_of(build_paragraphs([full_page(1), p])) == [
        ["ისეთ რამეს აკეთებდნენ მაგიდის ქვეშ ფეხით,", "ყველაფერი ზანზარებდა, გრგვინვა იყო მეხის."]
    ]


def test_narration_after_verse_is_left_out() -> None:
    song = ["ვერაფრით წინ ვერ წავედი,", "ესეც ვოლტერის ბრალია,", "ჩემს ბედს გაუტყდა ბორბალი,"]
    song.append("ესეც სულ რუსოს ბრალია.")
    p = verse_page(*song, "გავროში მღეროდა, ისინი ესროდნენ.")
    assert verse_of(build_paragraphs([full_page(1), p])) == [song]


def test_speech_inside_a_song_stays_in_it() -> None:
    song = [
        "ო, თეთრო ვარდო, პაწაწინა ყვავილო,",
        "ო, თეთრო ვარდო, ნაზო ყვავილო,",
        "- ტილო გარეცხე!",
        "- სად გავრეცხო?",
        "კაბის საკერად მოემზადე,",
        "კაბას სამკერდეც მიაყოლე,",
    ]
    p = verse_page(*song, intro="თან მღეროდა:")
    assert verse_of(build_paragraphs([full_page(1), p])) == [song]


def test_verse_doesnt_end_with_the_speech_after_it() -> None:
    p = verse_page(
        "წვა-დაგვაში გაატარა დრონი,",
        "დღე და ღამე ტვირთი ზიდა,",
        "არც აჭმევდნენ, არც ასმევდნენ,",
        "სიკვდილის დროს მათრახი სცეს,",
        "- საწყალი ცხენი, - ამოიოხრა.",
        "დალიამ იუცხოვა ეს სიბრალული:",
        intro="დაიწყო:",
    )
    [verse] = verse_of(build_paragraphs([full_page(1), p]))
    assert verse[-1] == "სიკვდილის დროს მათრახი სცეს,"


def test_page_of_short_lines_keeps_the_books_margins() -> None:
    # Measured alone, this page would take the indent for its margin and miss it.
    p = page(
        2,
        line(100, "ხელი მოაწერინა:", INDENT, 200),
        line(112, "„ბატონო ტენარდიე,", INDENT, 150),
        line(124, "ჩააბარეთ ჩემი კოზეტი.", INDENT, 200),
        line(136, "ფანტინი“.", INDENT, 120),
    )
    assert texts([full_page(1), p])[1:] == [
        "ხელი მოაწერინა:",
        "„ბატონო ტენარდიე,",
        "ჩააბარეთ ჩემი კოზეტი.",
        "ფანტინი“.",
    ]


def test_chapter_number_stands_alone() -> None:
    p = page(1, line(100, "XII", x1=80), line(114, "სტეპან არკადიჩი პირუთვნელი იყო."))
    assert texts([p]) == ["XII", "სტეპან არკადიჩი პირუთვნელი იყო."]


def test_text_right_after_a_label_starts_a_paragraph() -> None:
    p = page(1, line(100, "წინათქმა", x1=100), line(112, "ამ წიგნში ჰანს კასტორპის"))
    p.lines.append(line(124, "თავგადასავალი გვინდა გიამბოთ.", x1=200))
    assert texts([p]) == ["წინათქმა", "ამ წიგნში ჰანს კასტორპის თავგადასავალი გვინდა გიამბოთ."]


def test_line_of_text_starting_with_a_label_word_carries_on() -> None:
    p = page(
        1, line(100, "თავი მეორე სართულის ფანჯრიდან გადმოყო და"), line(112, "დაიძახა.", x1=100)
    )
    assert texts([p]) == ["თავი მეორე სართულის ფანჯრიდან გადმოყო და დაიძახა."]


def lines_page(number: int, rows: list[tuple[float, str, float]], x0: float = LEFT) -> Page:
    """A page of lines (y, text, x1), all from the left margin."""
    return page(number, *(line(y, text, x0=x0, x1=x1) for y, text, x1 in rows))


def spaced_book(step: float, joined_at: int | None = None) -> list[Page]:
    """Twelve paragraphs of three full lines, set apart by a wider step, no indent."""
    rows = []
    y = 40.0
    for number in range(12):
        for row in range(3):
            end = "." if row == 2 and number != joined_at else ""
            rows.append((y, f"Paragraph {number} line {row}{end}", RIGHT))
            y += 14
        y += step - 14
    return [lines_page(1, rows)]


def test_space_between_paragraphs_starts_one() -> None:
    # Every line is full, so only the space tells where paragraphs end.
    paragraphs = texts(spaced_book(22))
    assert len(paragraphs) == 12
    assert paragraphs[0] == "Paragraph 0 line 0 Paragraph 0 line 1 Paragraph 0 line 2."


def test_sentence_running_on_across_the_space_carries_on() -> None:
    paragraphs = texts(spaced_book(22, joined_at=4))
    assert len(paragraphs) == 11
    assert "Paragraph 4 line 2 Paragraph 5 line 0" in paragraphs[4]


def test_space_mid_sentence_in_a_loosely_spaced_book_is_no_break() -> None:
    # A Word export: space after every second line, half the time mid-sentence.
    rows = []
    y = 40.0
    for number in range(16):
        end = "." if number % 2 else ""
        rows.append((y, f"Line {number} of text", 350.0))
        rows.append((y + 18, f"and more of it{end}", 360.0))
        y += 46
    paragraphs = texts([lines_page(1, rows)])
    assert paragraphs[0] == "Line 0 of text and more of it Line 1 of text and more of it."
    assert len(paragraphs) == 8


def justified_page(*extra: tuple[float, str, float]) -> Page:
    rows = [(40 + 14 * row, f"Justified text line {row}", RIGHT) for row in range(30)]
    return lines_page(1, rows + list(extra))


def test_justified_line_a_little_short_ends_the_paragraph() -> None:
    p = justified_page((460, "It ends a word short.", RIGHT - 8), (474, "Next one.", RIGHT))
    *_, last, following = texts([p])
    assert last.endswith("line 29 It ends a word short.")
    assert following == "Next one."


def test_line_opening_with_a_full_stop_ends_the_sentence_above() -> None:
    p = page(
        1,
        line(100, "Est modus in rebus", x0=INDENT, x1=150),
        line(114, ". დიახ, სადილსაც კი ბოლო უნდა ჰქონდეს.", x0=INDENT, x1=300),
    )
    assert texts([p]) == ["Est modus in rebus. დიახ, სადილსაც კი ბოლო უნდა ჰქონდეს."]


def test_word_set_apart_mid_sentence_carries_on() -> None:
    p = page(
        1,
        line(100, "მელოტს. ყველაფერს საზღვარი უნდა ჰქონდეს", x1=230),
        line(114, "Est modus in rebus", x0=INDENT, x1=150),
        line(128, ". დიახ, სადილსაც კი ბოლო უნდა ჰქონდეს. ვაშლის ქადა", x0=INDENT),
        line(142, "ძალიან გიყვართ.", x1=150),
    )
    assert texts([p]) == [
        "მელოტს. ყველაფერს საზღვარი უნდა ჰქონდეს Est modus in rebus. დიახ, სადილსაც კი"
        " ბოლო უნდა ჰქონდეს. ვაშლის ქადა ძალიან გიყვართ."
    ]


def test_quote_opened_at_a_line_end_carries_on() -> None:
    p = page(
        1,
        line(100, "გამოაქანდაკეს სიტყვა „აღსდგა“ - „", x1=200),
        line(114, "Redivivus", x0=INDENT, x1=100),
        line(128, "“; პიე, რომელიც ცხოვრობდა ტერეზის ქ. #4-ში, ამზადებდა", x0=INDENT),
        line(142, "კრებებს.", x1=150),
    )
    assert texts([p]) == [
        "გამოაქანდაკეს სიტყვა „აღსდგა“ - „Redivivus“; პიე, რომელიც ცხოვრობდა ტერეზის ქ."
        " #4-ში, ამზადებდა კრებებს."
    ]


def test_english_opening_quote_starts_a_paragraph() -> None:
    p = page(
        1,
        line(100, "He said nothing.", x1=150),
        line(114, "“Come in,” she said.", x0=INDENT, x1=200),
    )
    assert texts([p]) == ["He said nothing.", "“Come in,” she said."]


def test_dash_alone_on_its_line_opens_the_speech_below() -> None:
    p = page(1, line(100, "-", x0=INDENT, x1=70), line(114, "Vermis sum.", x0=INDENT, x1=150))
    assert texts([p]) == ["- Vermis sum."]


def test_scene_break_stands_alone() -> None:
    p = page(1, line(100, "The end of it.", x1=150), line(114, "*", x1=60), line(128, "Then"))
    paragraphs = build_paragraphs([p])
    assert [x.text for x in paragraphs] == ["The end of it.", "*", "Then"]
    assert paragraphs[1].scene_break


def test_heading_set_in_the_text_stands_apart() -> None:
    p = justified_page(
        (460, "The section ends.", 200),
        (494, "Restaurant", 120),
        (508, "Bright and cosy, the restaurant", RIGHT),
        (522, "was on the right.", 200),
    )
    paragraphs = build_paragraphs([p])
    assert [x.text for x in paragraphs[-2:]] == [
        "Restaurant",
        "Bright and cosy, the restaurant was on the right.",
    ]
    assert paragraphs[-2].apart


def test_heading_set_in_the_text_without_space() -> None:
    p = justified_page(
        (460, "The orchestra played a polka.", 300),
        (474, "Hippe", 80),
        (488, "So went the Sundays up there, and", RIGHT),
    )
    paragraphs = build_paragraphs([p])
    assert paragraphs[-2].text == "Hippe"
    assert paragraphs[-2].apart


def test_word_left_before_a_paragraph_space_is_not_a_heading() -> None:
    p = justified_page(
        (460, "The section ends.", 300),
        (474, "Hephaestus", 80),
        (502, "152. This Psammetichus had fled before,", RIGHT),
    )
    paragraphs = build_paragraphs([p])
    assert not any(x.apart for x in paragraphs)


def test_first_line_after_a_space_is_not_a_heading() -> None:
    p = justified_page(
        (460, "The section ends.", 200),
        (510, "3. Then, when the Ionians asked Histiaeus why", RIGHT - 40),
        (524, "he had urged Aristagoras on so eagerly, he hid", RIGHT),
        (538, "the reason.", 120),
    )
    assert texts([p])[-1] == (
        "3. Then, when the Ionians asked Histiaeus why he had urged Aristagoras on so eagerly,"
        " he hid the reason."
    )


def test_next_numbered_section_starts_a_paragraph() -> None:
    first = page(1, line(500, "28. It was so."), line(514, "And the Lydians were subdued."))
    second = page(2, line(40, "29. When Croesus had subdued them,"), line(54, "Sardis grew."))
    assert texts([first, second]) == [
        "28. It was so. And the Lydians were subdued.",
        "29. When Croesus had subdued them, Sardis grew.",
    ]


def test_number_out_of_sequence_carries_on() -> None:
    first = page(1, line(500, "28. It was so."), line(514, "In the year"))
    second = page(2, line(40, "546. they came.", x1=150))
    assert texts([first, second]) == ["28. It was so. In the year 546. they came."]


def test_heading_in_capitals_before_its_translation() -> None:
    p = justified_page(
        (460, "The feeling had long gone.", RIGHT),
        (474, "OPERATIONES SPIRITUALES", 200),
        (488, "(Spiritual exercises (Lat.).) Naphta was born in a small town", RIGHT),
    )
    paragraphs = build_paragraphs([p])
    assert paragraphs[-2].text == "OPERATIONES SPIRITUALES"
    assert paragraphs[-2].apart


def test_text_before_a_bracketed_translation_carries_on() -> None:
    p = justified_page(
        (460, "The feeling had long gone.", RIGHT),
        (474, "nothing but prima materia", 200),
        (488, "(the first matter (Lat.).) and so it went on and on and on", RIGHT),
    )
    assert "gone. nothing but prima materia (the first matter" in texts([p])[-1]
