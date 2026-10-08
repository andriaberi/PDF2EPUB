import re
from os.path import commonprefix

from pdf2epub.paragraphs import Paragraph
from pdf2epub.paragraphs.builder import join

from .models import Note, Section

# Words the notes at the end of a book (or of a volume) are headed with.
TITLES = {"შენიშვნები", "notes", "endnotes"}

# A note's mark in the text, glued to the word it explains: "ფრეილინა[1]".
MARK = re.compile(r"\[(\d+)\]")

# A note starts with its mark and a space, at the start of a paragraph or after
# the last note: notes printed one under another often read as a single paragraph.
# Some PDFs keep a stray superscript after the mark: "[24]1 საამო ღამეს".
NOTE_START = re.compile(r"(?:^|(?<=\s))\[(\d+)\]\d*\s+")

# Notes may instead be keyed by the page of the printed book they explain, a word on
# it marked with a star: "გვ. 45. ფრანშკონტე _ ..." for "ფრანშკონტეში.*". Between
# the title and the first note there may be a line or two, like the book's title.
PAGE_KEY = re.compile(r"^(?:გვ|p|pp|page)\.?\s*\d+\.\s*", re.IGNORECASE)
MAX_SUBTITLE_LINES = 2
STAR = re.compile(r"\*")

# A note explains a term, written before a dash: "ფრანშკონტე _ აღმოსავლეთ ...".
TERM_END = re.compile(r"\s[_–—]\s")
WORD = re.compile(r"[^\W\d_]{3,}")
ROMAN = re.compile(r"[IVXLCDM]+")
APOSTROPHES = re.compile(r"['’]")

# A note ends a sentence; one that doesn't goes on in the paragraph after it, as when
# each printed line of a page reads as a paragraph of its own.
NOTE_ENDS = (".", "!", "?", "…", "»", "“", ")")

# A marked word is the term's word in another case ("ჰელვეციის" for "ჰელვეცია") when
# they share this many first letters, and differ in at most this many after them.
MIN_SHARED = 3
MAX_ENDING = 3

# Notes printed a little out of the order of their marks are looked for this many
# notes either side of where the order puts them first, then anywhere.
REORDERED = 3

# Notes without a title are known by their numbers: at least this many paragraphs in
# a row starting "[1] ", "[2] ", "[3] ".
MIN_UNTITLED_NOTES = 3


def extract_notes(sections: list[Section]) -> list[Note]:
    """Take the notes out of the text and link the marks in the text to them.

    A book may print notes at the end of each volume; the marks before a block of
    notes refer to that block, so numbering may start again after it.
    """
    notes: list[Note] = []
    waiting: list[Section] = []  # sections whose marks the next block of notes explains
    for index, section in enumerate(sections):
        if (keyed := find_keyed_block(section.paragraphs)) is not None:
            start, first = keyed
            entries = section.paragraphs[first:]
            del section.paragraphs[start:]
            notes.extend(link_stars(sections[: index + 1], entries, len(notes)))
            waiting = []
            continue
        waiting.append(section)
        while (block := find_block(section.paragraphs)) is not None:
            start, first, end = block
            found = {
                mark: Note(f"note-{len(notes) + number}", mark, text)
                for number, (mark, text) in enumerate(
                    split_notes(section.paragraphs[first:end]), start=1
                )
            }
            notes.extend(found.values())
            del section.paragraphs[start:end]
            for marked in waiting:
                link_marks(marked, found)
            waiting = [section]
    return notes


def find_block(paragraphs: list[Paragraph]) -> tuple[int, int, int] | None:
    """Where a block of notes is, with its title if it has one: [start, end), the
    notes themselves from `first` on.

    A long note may go on in a paragraph of its own, so the notes reach the last
    paragraph that starts one.
    """
    for index, paragraph in enumerate(paragraphs):
        titled = (
            paragraph.text.strip().casefold() in TITLES
            and index + 1 < len(paragraphs)
            and NOTE_START.match(paragraphs[index + 1].text) is not None
        )
        if not titled and not starts_numbered_notes(paragraphs[index:]):
            continue
        first = index + 1 if titled else index
        starts = [
            number
            for number in range(first, len(paragraphs))
            if NOTE_START.match(paragraphs[number].text)
        ]
        return index, first, starts[-1] + 1
    return None


def starts_numbered_notes(paragraphs: list[Paragraph]) -> bool:
    """Notes printed without a title: "[1] ...", "[2] ...", "[3] ..." one under another."""
    wanted = [str(number) for number in range(1, MIN_UNTITLED_NOTES + 1)]
    marks = [NOTE_START.match(p.text) for p in paragraphs[:MIN_UNTITLED_NOTES]]
    return [match.group(1) if match else None for match in marks] == wanted


def split_notes(paragraphs: list[Paragraph]) -> list[tuple[str, str]]:
    """ "[1] ფრეილინა – ... [2] ლივრეანი – ..." as ("1", "ფრეილინა – ..."), ("2", ...)."""
    text = " ".join(paragraph.text for paragraph in paragraphs)
    starts = list(NOTE_START.finditer(text))
    return [
        (start.group(1), text[start.end() : following.start() if following else None].strip())
        for start, following in zip(starts, [*starts[1:], None], strict=True)
    ]


def link_marks(section: Section, notes: dict[str, Note]) -> None:
    """Record which notes the section's marks refer to, the first block's for each mark."""
    for paragraph in section.paragraphs:
        for mark in MARK.findall(paragraph.text):
            if mark in notes:
                section.notes.setdefault(mark, notes[mark])


def find_keyed_block(paragraphs: list[Paragraph]) -> tuple[int, int] | None:
    """Where notes keyed by page start, with their title, and their first note.

    They run to the end of the book.
    """
    for index, paragraph in enumerate(paragraphs):
        if paragraph.text.strip().casefold() not in TITLES:
            continue
        following = paragraphs[index + 1 : index + 2 + MAX_SUBTITLE_LINES]
        for offset, candidate in enumerate(following, start=index + 1):
            if PAGE_KEY.match(candidate.text):
                return index, offset
    return None


def link_stars(sections: list[Section], entries: list[Paragraph], numbered: int) -> list[Note]:
    """Notes from the paragraphs of a block keyed by page, the starred words in the text
    linked to them.

    A star says only that a note exists; which one is told by the word it marks, which
    is the note's term, and by the order: marks and notes run through the book alike.
    Linked marks become numbered marks, "ფრანშკონტეში.[1]"; the others stay stars.
    """
    texts = [PAGE_KEY.sub("", text) for text in join_broken(entries)]
    terms = [TERM_END.split(text, maxsplit=1)[0] for text in texts]
    stars = [
        (section, paragraph, match.start())
        for section in sections
        for paragraph in section.paragraphs
        if not paragraph.verse and not paragraph.scene_break
        for match in STAR.finditer(paragraph.text)
    ]
    words = [marked_words(paragraph.text[:at]) for _, paragraph, at in stars]
    pairs = match_terms(words, terms)

    marks = {note: str(numbered + rank) for rank, note in enumerate(sorted(pairs.values()), 1)}
    notes = [
        Note(f"note-{numbered + number}", marks.get(number - 1, ""), text)
        for number, text in enumerate(texts, start=1)
    ]
    # Replace each star from the paragraph's end, so the places of the others hold.
    for star in sorted(pairs, key=lambda star: -stars[star][2]):
        section, paragraph, at = stars[star]
        note = notes[pairs[star]]
        paragraph.text = f"{paragraph.text[:at]}[{note.mark}]{paragraph.text[at + 1 :]}"
        section.notes[note.mark] = note
    return notes


def join_broken(entries: list[Paragraph]) -> list[str]:
    """The notes' texts, a note broken over paragraphs joined up again."""
    texts: list[str] = []
    for entry in entries:
        if texts and not texts[-1].endswith(NOTE_ENDS) and not PAGE_KEY.match(entry.text):
            texts[-1] = join(texts[-1], entry.text)
        else:
            texts.append(entry.text)
    return texts


def marked_words(before: str) -> list[str]:
    """The words a star may mark: the last before it, or the one before that when the
    last is a numeral or a case ending, as in "ანრი III-ისა*"."""
    return [word for word in letter_words(before) if not ROMAN.fullmatch(word)][-2:][::-1]


def letter_words(text: str) -> list[str]:
    """Words of three letters or more, "დ’ობინიე" read as "დობინიე"."""
    return WORD.findall(APOSTROPHES.sub("", text))


def match_terms(words: list[list[str]], terms: list[str]) -> dict[int, int]:
    """Which note each mark refers to, as {mark: note}: the pairing of marks and notes
    in order that scores best, then marks left over paired with the notes
    left over, those near where the order puts them first."""
    scores = [[term_score(marked, term) for term in terms] for marked in words]
    # best[i][j]: the best score of marks i.. paired with notes j..
    best = [[0] * (len(terms) + 1) for _ in range(len(words) + 1)]
    for i in range(len(words) - 1, -1, -1):
        for j in range(len(terms) - 1, -1, -1):
            paired = best[i + 1][j + 1] + scores[i][j] if scores[i][j] else 0
            best[i][j] = max(best[i + 1][j], best[i][j + 1], paired)

    pairs: dict[int, int] = {}
    i = j = 0
    while i < len(words) and j < len(terms):
        if scores[i][j] and best[i][j] == best[i + 1][j + 1] + scores[i][j]:
            pairs[i] = j
            i, j = i + 1, j + 1
        elif best[i][j] == best[i + 1][j]:
            i += 1
        else:
            j += 1

    taken = set(pairs.values())
    for mark in range(len(words)):
        if mark in pairs:
            continue
        before = max((pairs[m] for m in pairs if m < mark), default=0)
        after = min((pairs[m] for m in pairs if m > mark), default=len(terms) - 1)
        free = [note for note in range(len(terms)) if note not in taken and scores[mark][note]]
        nearby = [note for note in free if before - REORDERED <= note <= after + REORDERED]
        if candidates := nearby or free:
            note = max(candidates, key=lambda note: scores[mark][note])
            pairs[mark] = note
            taken.add(note)

    # A mark that matches no term, alone between two paired marks whose notes have one
    # note between them, is that note's: it marks a word further back, "პიემონტის და
    # ესპანეთის რევოლუციონერებს ... დანაშაულით?*".
    for mark in range(len(words)):
        if mark in pairs or mark - 1 not in pairs or mark + 1 not in pairs:
            continue
        note = pairs[mark - 1] + 1
        if pairs[mark + 1] == note + 1 and note not in taken:
            pairs[mark] = note
            taken.add(note)
    return pairs


def term_score(marked: list[str], term: str) -> int:
    """How well the marked words match the term: the letters each shares with a word of
    the term, if they are the same word in different cases. The word right before the
    star counts double, so "წმ. ბონავენტურას*" is "ბონავენტურა" before "წმ. ავგუსტინე"."""
    score = 0
    for weight, word in zip((2, 1), marked, strict=False):
        best = 0
        for term_word in letter_words(term):
            shared = len(commonprefix([word.casefold(), term_word.casefold()]))
            if shared >= MIN_SHARED and shared >= min(len(word), len(term_word)) - MAX_ENDING:
                best = max(best, shared)
        score += weight * best
    return score
