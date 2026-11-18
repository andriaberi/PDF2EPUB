import re

from pdf2epub.languages import all_words, any_of
from pdf2epub.paragraphs import Paragraph
from pdf2epub.paragraphs.builder import join
from pdf2epub.pdf import Footnote
from pdf2epub.pdf.text import NOTE_MARK

from .models import Note, Section

TITLES = all_words("notes_titles")
NOTE_START = re.compile(r"(?:^|(?<=\s))\[(\d+)\]\d*\s+")
PAGE_KEY = re.compile(
    rf"^(?:{any_of(all_words('page_abbreviations'))})\.?\s*\d+\.\s*", re.IGNORECASE
)
MAX_SUBTITLE_LINES = 2
STAR = re.compile(r"\*")
TERM_END = re.compile(r"\s[_–—]\s")
WORD = re.compile(r"[^\W\d_]{3,}")
ROMAN = re.compile(r"[IVXLCDM]+")
APOSTROPHES = re.compile(r"['’]")
NOTE_ENDS = (".", "!", "?", "…", "»", "“", ")")
MIN_SHARED = 3
MAX_ENDING = 3
REORDERED = 3
MIN_UNTITLED_NOTES = 3


def extract_notes(sections: list[Section]) -> list[Note]:
    notes: list[Note] = []
    waiting: list[Section] = []
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


def link_footnotes(sections: list[Section], footnotes: list[Footnote]) -> list[Note]:
    notes = {f.mark: Note(f"footnote-{f.mark}", f.mark, f.text) for f in footnotes}
    for section in sections:
        link_marks(section, notes)
    return list(notes.values())


def find_block(paragraphs: list[Paragraph]) -> tuple[int, int, int] | None:
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
    wanted = [str(number) for number in range(1, MIN_UNTITLED_NOTES + 1)]
    marks = [NOTE_START.match(p.text) for p in paragraphs[:MIN_UNTITLED_NOTES]]
    return [match.group(1) if match else None for match in marks] == wanted


def split_notes(paragraphs: list[Paragraph]) -> list[tuple[str, str]]:
    text = " ".join(paragraph.text for paragraph in paragraphs)
    starts = list(NOTE_START.finditer(text))
    return [
        (start.group(1), text[start.end() : following.start() if following else None].strip())
        for start, following in zip(starts, [*starts[1:], None], strict=True)
    ]


def link_marks(section: Section, notes: dict[str, Note]) -> None:
    for paragraph in section.paragraphs:
        for mark in NOTE_MARK.findall(paragraph.text):
            if mark in notes:
                section.notes.setdefault(mark, notes[mark])


def find_keyed_block(paragraphs: list[Paragraph]) -> tuple[int, int] | None:
    for index, paragraph in enumerate(paragraphs):
        if paragraph.text.strip().casefold() not in TITLES:
            continue
        following = paragraphs[index + 1 : index + 2 + MAX_SUBTITLE_LINES]
        for offset, candidate in enumerate(following, start=index + 1):
            if PAGE_KEY.match(candidate.text):
                return index, offset
    return None


def link_stars(sections: list[Section], entries: list[Paragraph], numbered: int) -> list[Note]:
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
    for star in sorted(pairs, key=lambda star: -stars[star][2]):
        section, paragraph, at = stars[star]
        note = notes[pairs[star]]
        paragraph.text = f"{paragraph.text[:at]}[{note.mark}]{paragraph.text[at + 1 :]}"
        section.notes[note.mark] = note
    return notes


def join_broken(entries: list[Paragraph]) -> list[str]:
    texts: list[str] = []
    for entry in entries:
        if texts and not texts[-1].endswith(NOTE_ENDS) and not PAGE_KEY.match(entry.text):
            texts[-1] = join(texts[-1], entry.text)
        else:
            texts.append(entry.text)
    return texts


def marked_words(before: str) -> list[str]:
    return [word for word in letter_words(before) if not ROMAN.fullmatch(word)][-2:][::-1]


def letter_words(text: str) -> list[str]:
    return WORD.findall(APOSTROPHES.sub("", text))


def match_terms(words: list[list[str]], terms: list[str]) -> dict[int, int]:
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

    for mark in range(len(words)):
        if mark in pairs or mark - 1 not in pairs or mark + 1 not in pairs:
            continue
        note = pairs[mark - 1] + 1
        if pairs[mark + 1] == note + 1 and note not in taken:
            pairs[mark] = note
            taken.add(note)
    return pairs


def term_score(marked: list[str], term: str) -> int:
    score = 0
    for weight, word in zip((2, 1), marked, strict=False):
        best = 0
        for term_word in letter_words(term):
            shared = shared_start(word.casefold(), term_word.casefold())
            if shared >= MIN_SHARED and shared >= min(len(word), len(term_word)) - MAX_ENDING:
                best = max(best, shared)
        score += weight * best
    return score


def shared_start(word: str, other: str) -> int:
    count = 0
    for a, b in zip(word, other, strict=False):
        if a != b:
            break
        count += 1
    return count
