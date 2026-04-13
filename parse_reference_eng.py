# -*- coding: utf-8 -*-
import re

# ── Spoken Numeral Mode ──
# When True, "john 3 16" (no colon, no 'verse' keyword) is treated as John 3:16.
# Default OFF — call set_spoken_numeral_mode(True) to enable, or wire through configure().
SPOKEN_NUMERAL_MODE: bool = False


def set_spoken_numeral_mode(enabled: bool) -> None:
    global SPOKEN_NUMERAL_MODE
    SPOKEN_NUMERAL_MODE = enabled

# ── BOOK ALIASES ──
# Canonical names + common ASR (Deepgram) mishearings, phonetic spellings,
# Indian-English variants, and alternate names. Keys are lowercase.
BOOKS_ENG = {
    # ── Old Testament ──
    "genesis": "Genesis", "genesus": "Genesis", "genasis": "Genesis", "genisis": "Genesis",
    "exodus": "Exodus", "exodous": "Exodus", "exodas": "Exodus",
    "leviticus": "Leviticus", "levitacus": "Leviticus", "leviticas": "Leviticus",
    "numbers": "Numbers",
    "deuteronomy": "Deuteronomy", "deutronomy": "Deuteronomy", "deutronmy": "Deuteronomy",
    "joshua": "Joshua", "joshwa": "Joshua", "josua": "Joshua",
    "judges": "Judges",
    "ruth": "Ruth",
    "1 samuel": "1 Samuel", "first samuel": "1 Samuel", "one samuel": "1 Samuel",
    "2 samuel": "2 Samuel", "second samuel": "2 Samuel", "two samuel": "2 Samuel",
    "1 kings": "1 Kings", "first kings": "1 Kings", "one kings": "1 Kings",
    "2 kings": "2 Kings", "second kings": "2 Kings", "two kings": "2 Kings",
    "1 chronicles": "1 Chronicles", "first chronicles": "1 Chronicles", "one chronicles": "1 Chronicles",
    "2 chronicles": "2 Chronicles", "second chronicles": "2 Chronicles", "two chronicles": "2 Chronicles",
    "cronicles": "1 Chronicles", "chronicals": "1 Chronicles",
    "ezra": "Ezra", "ezrah": "Ezra",
    "nehemiah": "Nehemiah", "nehemia": "Nehemiah", "nehimia": "Nehemiah", "nehemiahs": "Nehemiah",
    "esther": "Esther", "ester": "Esther",
    "job": "Job",
    "psalm": "Psalm", "psalms": "Psalm",
    "sams": "Psalm", "sam s": "Psalm", "sam's": "Psalm",
    "saams": "Psalm", "saam": "Psalm",  # Fix 7: Indian-accent variants
    "songs": "Psalm",  # Fix 9: Indian-accent "songs" for Psalms (standalone only — "song of" still hits SoS first due to sort-longest-first in _get_book_keys_re)


    "proverbs": "Proverbs", "provberbs": "Proverbs",
    "ecclesiastes": "Ecclesiastes", "ecclesiast": "Ecclesiastes", "ecclesiates": "Ecclesiastes",
    "song of solomon": "Song of Solomon", "songs of solomon": "Song of Solomon",
    "song of songs": "Song of Solomon", "song of song": "Song of Solomon",
    "song songs": "Song of Solomon", "canticles": "Song of Solomon", "sos": "Song of Solomon",
    "isaiah": "Isaiah", "isaia": "Isaiah", "isaya": "Isaiah", "isaiahs": "Isaiah", "isiah": "Isaiah",
    "jeremiah": "Jeremiah", "jerimiah": "Jeremiah", "jeremia": "Jeremiah", "jerimiahs": "Jeremiah",
    "lamentations": "Lamentations", "lamentation": "Lamentations",
    "ezekiel": "Ezekiel", "ezakiel": "Ezekiel", "ezekeal": "Ezekiel", "ezequiel": "Ezekiel",
    "daniel": "Daniel", "danial": "Daniel", "danel": "Daniel",
    "hosea": "Hosea", "hosia": "Hosea", "hoseah": "Hosea",
    "joel": "Joel", "joels": "Joel",
    "amos": "Amos",
    "obadiah": "Obadiah", "obadia": "Obadiah", "obadias": "Obadiah",
    "jonah": "Jonah", "jonas": "Jonah",
    "micah": "Micah", "mica": "Micah",
    "nahum": "Nahum",
    "habakkuk": "Habakkuk", "habakuk": "Habakkuk", "habacuc": "Habakkuk",
    "zephaniah": "Zephaniah", "zepheniah": "Zephaniah", "zephania": "Zephaniah",
    "haggai": "Haggai", "hagai": "Haggai", "haggia": "Haggai",
    "zechariah": "Zechariah", "zecharia": "Zechariah", "zecariah": "Zechariah", "zachariah": "Zechariah",
    "malachi": "Malachi", "malachai": "Malachi", "malaki": "Malachi",
    # ── New Testament ──
    "matthew": "Matthew", "mathew": "Matthew", "mattheww": "Matthew",
    "mark": "Mark",
    "luke": "Luke", "luk": "Luke", "lukes": "Luke",
    "john": "John", "jon": "John",
    "acts": "Acts",
    "romans": "Romans", "romens": "Romans", "romanss": "Romans", "roma-ns": "Romans",
    "1 corinthians": "1 Corinthians", "first corinthians": "1 Corinthians", "one corinthians": "1 Corinthians",
    "2 corinthians": "2 Corinthians", "second corinthians": "2 Corinthians", "two corinthians": "2 Corinthians",
    "corinthians": "1 Corinthians", "corinthans": "1 Corinthians", "corithians": "1 Corinthians",
    "corenthians": "1 Corinthians", "corenthains": "1 Corinthians",
    "galatians": "Galatians", "galations": "Galatians", "galatans": "Galatians", "gala-tians": "Galatians",
    "ephesians": "Ephesians", "ephesans": "Ephesians", "efesians": "Ephesians", "ephesian": "Ephesians",
    "philippians": "Philippians", "phillipians": "Philippians", "philipians": "Philippians", "phillippians": "Philippians",
    "colossians": "Colossians", "colosians": "Colossians", "collosians": "Colossians",
    "collisians": "Colossians", "colossions": "Colossians",  # Fix 7: new fuzzy variants

    "collosions": "Colossians", "colosions": "Colossians", "colloshans": "Colossians", "coloshians": "Colossians",
    "colossions": "Colossians",
    "1 thessalonians": "1 Thessalonians", "first thessalonians": "1 Thessalonians", "one thessalonians": "1 Thessalonians",
    "1 thess": "1 Thessalonians", "first thess": "1 Thessalonians", "one thess": "1 Thessalonians",
    "2 thessalonians": "2 Thessalonians", "second thessalonians": "2 Thessalonians", "two thessalonians": "2 Thessalonians",
    "thessalonians": "1 Thessalonians", "thesalonians": "1 Thessalonians", "thesolonians": "1 Thessalonians",
    "1 timothy": "1 Timothy", "first timothy": "1 Timothy", "one timothy": "1 Timothy",
    "2 timothy": "2 Timothy", "second timothy": "2 Timothy", "two timothy": "2 Timothy",
    "timothy": "1 Timothy", "timoty": "1 Timothy", "timothys": "1 Timothy",
    "titus": "Titus",
    "philemon": "Philemon", "philemonn": "Philemon",
    "hebrews": "Hebrews",
    "james": "James",
    "1 peter": "1 Peter", "first peter": "1 Peter", "one peter": "1 Peter",
    "2 peter": "2 Peter", "second peter": "2 Peter", "two peter": "2 Peter",
    "1 john": "1 John", "first john": "1 John", "one john": "1 John",
    "2 john": "2 John", "second john": "2 John", "two john": "2 John",
    "3 john": "3 John", "third john": "3 John", "three john": "3 John",
    "jude": "Jude", "judes": "Jude",
    "revelation": "Revelation", "revelations": "Revelation", "revelaton": "Revelation", "revilation": "Revelation",
}

# ── Bug 1: Maximum chapter counts per canonical book name ──
BOOK_CHAPTER_COUNTS = {
    "Genesis": 50, "Exodus": 40, "Leviticus": 27, "Numbers": 36, "Deuteronomy": 34,
    "Joshua": 24, "Judges": 21, "Ruth": 4,
    "1 Samuel": 31, "2 Samuel": 24, "1 Kings": 22, "2 Kings": 25,
    "1 Chronicles": 29, "2 Chronicles": 36,
    "Ezra": 10, "Nehemiah": 13, "Esther": 10, "Job": 42,
    "Psalm": 150, "Proverbs": 31, "Ecclesiastes": 12, "Song of Solomon": 8,
    "Isaiah": 66, "Jeremiah": 52, "Lamentations": 5, "Ezekiel": 48, "Daniel": 12,
    "Hosea": 14, "Joel": 3, "Amos": 9, "Obadiah": 1, "Jonah": 4, "Micah": 7,
    "Nahum": 3, "Habakkuk": 3, "Zephaniah": 3, "Haggai": 2, "Zechariah": 14, "Malachi": 4,
    "Matthew": 28, "Mark": 16, "Luke": 24, "John": 21, "Acts": 28, "Romans": 16,
    "1 Corinthians": 16, "2 Corinthians": 13, "Galatians": 6, "Ephesians": 6,
    "Philippians": 4, "Colossians": 4, "1 Thessalonians": 5, "2 Thessalonians": 3,
    "1 Timothy": 6, "2 Timothy": 4, "Titus": 3, "Philemon": 1, "Hebrews": 13,
    "James": 5, "1 Peter": 5, "2 Peter": 3, "1 John": 5, "2 John": 1, "3 John": 1,
    "Jude": 1, "Revelation": 22,
}

# ── Ordinals only for numbered-book prefixes ("first john", "second peter", etc.)
# NOTE: Do NOT add "one"/"two"/"three" here — they're handled by NUMBER_MAP
#       below and adding them here breaks compound numbers like "twenty two".
ORDINAL_WORDS = {"first": "1", "second": "2", "third": "3"}

# ── Number words → digits ──
NUMBER_MAP = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    # ── Indian-accent ASR mishearings ──
    "nayan": 9,  # Sarvam/Deepgram transcribes Malayalam-accented "nine" as "nayan"
    "nyan":  9,
}


def convert_word_numbers(text: str) -> str:
    """Convert spoken numbers to digits: "twenty five" → "25", "two hundred three" → "203", "one fifty" → "150"."""
    text = text.replace("-", " ")
    words = text.split()
    result = []
    i = 0
    while i < len(words):
        w = words[i]
        # "two hundred [three]" → 200/203
        if i + 1 < len(words) and w in NUMBER_MAP and words[i + 1] == "hundred":
            base = int(NUMBER_MAP[w]) * 100
            if i + 2 < len(words) and words[i + 2] in NUMBER_MAP:
                result.append(str(base + int(NUMBER_MAP[words[i + 2]])))
                i += 3
            else:
                result.append(str(base))
                i += 2
            continue
        # "one fifty" / "one twenty" → 150, 120 (hundreds when 1–9 + tens-word)
        # FIX 1: Do NOT fire when the following pattern is ones+tens+ones,
        # because "three twenty three" means chapter 3 verse 23, not 323.
        # Detect: if prev token in result was a non-number word (book name),
        # skip the hundreds combination so "collisians three twenty three" → "collisians 3 20 3"
        # then the colon-insertion in _insert_chapter_verse_colon handles it.
        if i + 1 < len(words) and w in NUMBER_MAP and words[i + 1] in NUMBER_MAP:
            fv = int(NUMBER_MAP[w])
            sv = int(NUMBER_MAP[words[i + 1]])
            if 1 <= fv <= 9 and sv >= 20 and sv % 10 == 0:
                # FIX 1: If preceded by a non-number word AND followed by a ones-word,
                # this is chapter(fv) + tens_verse + ones_verse — don't collapse to hundreds.
                prev_is_word = bool(result) and not result[-1].isdigit()
                next_is_ones = (i + 2 < len(words) and words[i + 2] in NUMBER_MAP
                                and 1 <= int(NUMBER_MAP[words[i + 2]]) <= 9)
                if prev_is_word and next_is_ones:
                    # Treat as separate: chapter digit + verse tens + verse ones
                    result.append(str(fv))
                    i += 1
                    continue
                combined = fv * 100 + sv
                if i + 2 < len(words) and words[i + 2] in NUMBER_MAP:
                    third = int(NUMBER_MAP[words[i + 2]])
                    if 1 <= third <= 9:
                        combined += third
                        i += 3
                        result.append(str(combined))
                        continue
                i += 2
                result.append(str(combined))
                continue
        # "twenty five" → 25 (tens + ones only)
        if i + 1 < len(words) and w in NUMBER_MAP and words[i + 1] in NUMBER_MAP:
            fv = int(NUMBER_MAP[w])
            sv = int(NUMBER_MAP[words[i + 1]])
            if fv >= 20 and fv % 10 == 0 and 1 <= sv <= 9:
                result.append(str(fv + sv))
                i += 2
                continue
        result.append(str(NUMBER_MAP[w]) if w in NUMBER_MAP else w)
        i += 1
    return " ".join(result)


# ── Range-indicator words that mean two digits are a chapter RANGE, not book:verse ──
_RANGE_WORDS_RE = re.compile(
    r'\b(?:through|thru|until|to)\b',
    re.IGNORECASE,
)

# ── All lowercase book-key aliases from BOOKS_ENG joined into one alternation RE ──
# Built lazily on first use so module import stays fast.
_BOOK_KEYS_RE: re.Pattern | None = None


def _get_book_keys_re() -> re.Pattern:
    global _BOOK_KEYS_RE
    if _BOOK_KEYS_RE is None:
        # Sort longest-first so multi-word keys ("song of solomon") match before shorter ones.
        keys = sorted(BOOKS_ENG, key=len, reverse=True)
        escaped = [re.escape(k) for k in keys]
        _BOOK_KEYS_RE = re.compile(r'(?:' + '|'.join(escaped) + r')', re.IGNORECASE)
    return _BOOK_KEYS_RE


def _insert_chapter_verse_colon(text: str) -> str:
    """
    SPOKEN_NUMERAL_MODE preprocessing:
    After digit-conversion, detect [book] [chap_digit] [verse_digit] with no colon already
    present and no range word between the two digits, then replace the space with ':' so the
    main regex can capture chapter:verse.

    Guards:
      - Range word (through/to/until/thru) between digits → skip (chapter range)
      - chap > 150 or verse > 176 → skip (implausible)
      - Already has ':' between the digits → skip
    """
    book_re = _get_book_keys_re()

    # Build a pattern: [book_key] [spaces] [chap] [spaces] [verse]
    # We capture group(1)=chap, group(2)=the whitespace between chapter and verse, group(3)=verse
    # and replace group(2) with ':' only when guards pass.
    pattern = re.compile(
        r'(?:' + book_re.pattern + r')'    # book (non-capturing)
        r'\s+(\d{1,3})'                    # chapter digit  → group 1
        r'(\s+)'                           # whitespace gap → group 2
        r'(\d{1,3})'                       # verse digit    → group 3
        r'(?=\s|$)',                       # followed by space or end
        re.IGNORECASE,
    )

    def _replacer(m: re.Match) -> str:
        chap_str  = m.group(len(m.groups()) - 2)   # second-to-last group
        gap       = m.group(len(m.groups()) - 1)   # last-but-one → whitespace
        verse_str = m.group(len(m.groups()))        # last group

        # Determine correct group indices (they vary based on how many book_re groups there are)
        # Use named extraction: chap is at index -3 from end, gap at -2, verse at -1
        chap  = int(chap_str)
        verse = int(verse_str)

        # Guard: plausibility
        if chap > 150 or verse > 176:
            return m.group(0)  # leave unchanged

        # Guard: range word in the gap
        if _RANGE_WORDS_RE.search(gap):
            return m.group(0)

        # Guard: colon already present in the gap
        if ':' in gap:
            return m.group(0)

        # Replace gap with ':' — produces "john 3:16"
        return m.group(0).replace(gap, ':', 1)

    # Count groups in the book_re pattern to compute correct offsets
    # Simpler: rebuild the pattern capturing all three targets explicitly
    book_pat = book_re.pattern  # already no capturing groups (all non-capturing in _get_book_keys_re)
    full_pat = re.compile(
        r'(?:(?:[123]\s+)?' + r'(?:' + book_pat + r')'  + r')'  # book (allows "1 peter" etc.)
        r'\s+'
        r'(\d{1,3})'       # group 1: chapter
        r'(\s+)'           # group 2: gap
        r'(\d{1,3})'       # group 3: verse
        r'(?=\s|$)',
        re.IGNORECASE,
    )

    def _sub(m: re.Match) -> str:
        chap      = int(m.group(1))
        gap       = m.group(2)
        verse     = int(m.group(3))

        if chap > 150 or verse > 176:
            return m.group(0)
        if _RANGE_WORDS_RE.search(gap):
            return m.group(0)
        if ':' in gap:
            return m.group(0)

        # Replace the whitespace gap with ':' preserving the surrounding text
        original = m.group(0)
        # gap spans from group(1).end to group(3).start within m.group(0)
        g1_end   = m.start(2) - m.start()
        g2_end   = m.end(2)   - m.start()
        return original[:g1_end] + ':' + original[g2_end:]

    return full_pat.sub(_sub, text)



def normalize_text(s: str) -> str:
    """Full normalization: lowercase, ordinal conversion, number conversion, noise removal."""
    s = s.lower()
    # Only replace "first/second/third" — NOT one/two/three (would break "twenty two" etc.)
    for word, num in ORDINAL_WORDS.items():
        s = re.sub(rf"\b{word}\b", num, s)
    # FIX 1: Protect verse/verses/versus with a colon placeholder BEFORE number conversion
    # so "three verse twenty three" becomes "3 : 23" not "3 20 3" → 323.
    # Using ':' directly is perfect — the regex that captures chapter:verse already expects it.
    s = re.sub(r'\b(verses?|versus)\b', ':', s, flags=re.IGNORECASE)
    # Strip punctuation/special chars → space (but preserve colons for verse numbers)
    s = re.sub(r"[^a-z0-9: ]", " ", s)
    # Convert spoken numbers to digits
    s = convert_word_numbers(s)
    # Spoken Numeral Mode: insert ':' between consecutive book+chapter+verse digit tokens
    if SPOKEN_NUMERAL_MODE:
        s = " ".join(s.split())
        s = _insert_chapter_verse_colon(s)
    # Bug 6: Recognize 'X and Y' as chapter:verse before noise filter strips 'and'
    s = re.sub(r'\b(\d+)\s+and\s+(\d+)\b', r'\1:\2', s)
    # FIX 1: Collapse spaced colons "3 : 23" → "3:23" so REF_RE can match
    s = re.sub(r'(\d)\s*:\s*(\d)', r'\1:\2', s)

    # Bug 6: "X and Y" → "X:Y" — recognize spoken 'chapter and verse' pattern
    # e.g. "twenty and twenty three" → "20:23", "5 and 6" → "5:6"
    # Apply before noise stripping so that 'and' is still present.
    s = re.sub(r'\b(\d{1,3})\s+and\s+(\d{1,3})\b', r'\1:\2', s)
    # Bug 5: Chapter/verse range-description suppressor — strip "chapter 1 to 6",
    # "chapters 3 through 7", "verses 1 to 10", etc. so they do not trigger a presentation.
    range_pat = re.compile(
        r'\b(?:chapters?|verses?)\s+\d+\s+(?:to|through|thru)\s+\d+\b',
        re.IGNORECASE,
    )
    if range_pat.search(s):
        import logging as _log
        _log.getLogger(__name__).debug(
            f"RANGE_DETECTED (suppressed): {range_pat.search(s).group()}"
        )
    s = range_pat.sub('', s)
    # Bug 7: Temporal duration suppressor — strip "2 years", "3 and a half months", etc.
    # so they cannot be mistaken for chapter or verse numbers.
    s = re.sub(
        r'\b\d+\s+(?:and\s+a\s+half\s+)?'
        r'(?:years?|months?|weeks?|days?|hours?|minutes?|seconds?)\b',
        '', s,
    )
    # Bug 6: Quantity reference suppressor — strip "3 things", "2 people", etc.
    s = re.sub(
        r'\b\d+\s+(?:things?|people|persons?|men|women|points?|times?|ways?|reasons?|parts?)\b',
        '', s,
    )
    # Bug 2: Ordinal-enumeration suppressor — strip "number 2", "point 3", "step 1", etc.
    # Must run AFTER convert_word_numbers so "number two" → "number 2" is already in s.
    s = re.sub(r'\b(?:number|point|step)\s+\d+\b', '', s)
    # Remove sermon filler / navigation words
    # NOTE: "of" is intentionally NOT stripped — needed for "Song of Songs", "Song of Solomon"
    # NOTE: "verse|verses|versus" are NOT stripped — required to accept chapter:verse (e.g. "Psalm 1 verse 50" vs "Psalm 150")
    noise = (
        r"\b(lets|let s|let us|read|the|a|an|chapter|chap|ch"
        r"|vs|forward|attention|to|now|our"
        r"|turn|open|look|see|go|pay|pages|bible|book|books"
        r"|words|word|says|said|saying|it|in|and|at|from"
        r"|today|we|will|are|is|was|epistle"
        r"|reading|ll|be)\b"
    )
    s = re.sub(noise, " ", s)
    # Bug 2: After noise stripping, remove residual "of " artifact that precedes a
    # numbered-book prefix (1/2/3) so "epistle of 2 Timothy" normalises to "2 timothy".
    s = re.sub(r'\bof\s+(?=[123] )', '', s)
    return " ".join(s.split())


def normalize_numbers_only(s: str) -> str:
    """Convert word numbers to digits only — no noise stripping (used for range detection)."""
    s = s.lower()
    for word, num in ORDINAL_WORDS.items():
        s = re.sub(rf"\b{word}\b", num, s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = convert_word_numbers(s)
    # Bug 2: Strip ordinal-enumeration patterns so "number 2" cannot become a chapter candidate
    s = re.sub(r'\b(?:number|point|step)\s+\d+\b', '', s)
    return " ".join(s.split())


def resolve_book(bookraw: str):
    """Return canonical book name or None. Uses word-boundary matching to avoid false positives."""
    b = bookraw.strip().lower()
    # Strip trailing verse/verses/versus if present
    b = re.sub(r'\s+(?:verse|verses|versus)$', '', b)
    # 1. Exact dict match (fastest path)
    if b in BOOKS_ENG:
        return BOOKS_ENG[b]
    # 2. Word-boundary substring search — keys and candidates must be ≥ 4 chars.
    #    \b prevents "acts" from matching inside "reacts", "facts", "distracts", etc.
    if len(b) >= 4:
        for key in BOOKS_ENG:
            if len(key) >= 4 and re.search(r"\b" + re.escape(key) + r"\b", b):
                return BOOKS_ENG[key]
    return None


# ── Main reference regex ──
# Verse number is only captured when preceded by ":" or by "verse"/"verses"/"versus"
# so "Psalms one fifty" → Psalm 150, not Psalm 1:50.
# Bug 6: Negative lookahead on chapter digit to prevent it from consuming the leading digit 
# of a numbered book (e.g. "pastor 1 peter" shouldn't match "pastor" as book and "1" as chapter)
_NUMBERED_BOOK_WORDS = "chronicles|corinthians|john|kings|peter|samuel|thess|thessalonians|timothy|mac|maccabees"
REF_RE = re.compile(
    r"(?P<book>(?:[123] )?[a-z]+(?:[a-z ]*)"
    r")"
    r"\s+"
    r"(?P<chap>\d{1,3})"
    rf"(?!\s+(?:{_NUMBERED_BOOK_WORDS})\b)"
    r"(?::(?P<verses>\d{1,3})|\s+(?:verse|verses|versus)\s+(?P<verses_word>\d{1,3}))?",
    re.IGNORECASE,
)


def parse_references(text: str):
    if not text:
        return []
    results = []
    t = normalize_text(text)
    for m in REF_RE.finditer(t):
        eng = resolve_book(m.group("book"))
        if eng:
            chap_int  = int(m.group("chap"))
            max_chap  = BOOK_CHAPTER_COUNTS.get(eng, 999)
            if chap_int > max_chap:
                continue
            ref = f"{eng} {m.group('chap')}"
            verses = m.group("verses") or m.group("verses_word")
            if verses:
                ref += f":{verses}"
            results.append(ref)
    return results


def parse_reference(text: str):
    refs = parse_references(text)
    return refs[0] if refs else None


# ── Self-test ──
if __name__ == "__main__":
    tests = [
        ("Turn to Romans chapter eight verse twenty eight",   "Romans 8:28"),
        ("John three verse sixteen",                          "John 3:16"),
        ("John three sixteen",                                "John 3"),   # no "verse" → chapter only
        ("First Corinthians thirteen verse four",             "1 Corinthians 13:4"),
        ("Isaiah fifty four verse six",                       "Isaiah 54:6"),
        ("Isaiah fifty four six",                             "Isaiah 54"), # no "verse" → chapter only
        ("Acts thirteen verse two",                           "Acts 13:2"),
        ("Let us read John one verses five",                  "John 1:5"),
        ("Jeremiah chapter nine verse one",                   "Jeremiah 9:1"),
        ("Jeremiah chapter twenty verse nine",                "Jeremiah 20:9"),
        # Phonetic / ASR
        ("Turn with me to Sam's nine",                        "Psalm 9"),
        ("Sam's Nayan verse one",                             "Psalm 9:1"),
        ("Sam's Nayan one to ten",                            "Psalm 9"),   # no "verse" → chapter only
        ("Sam's Nayan verse one to ten",                      "Psalm 9:1"),
        # Book name variants
        ("Song of songs chapter one verse one",               "Song of Solomon 1:1"),
        ("Song of Solomon chapter one verse two",             "Song of Solomon 1:2"),
        ("Canticles chapter two verse one",                   "Song of Solomon 2:1"),
        ("Revelations twenty two verse twenty",               "Revelation 22:20"),
        ("Deutronomy chapter six verse four",                 "Deuteronomy 6:4"),
        ("Ezakiel chapter thirty seven",                      "Ezekiel 37"),
        ("Hosea chapter three verse five",                    "Hosea 3:5"),
        # one/two/three as book prefixes (handled via NUMBER_MAP)
        ("one john chapter three verse sixteen",              "1 John 3:16"),
        ("two timothy chapter two verse fifteen",             "2 Timothy 2:15"),
        # Should NOT match
        ("We will be here for twenty four hours",             None),
        ("God calls and sets apart",                          None),
        ("Amen praise the Lord",                              None),
        # Bug 6 — 'X and Y' spoken chapter:verse
        ("Proverbs twenty and twenty three",                  "Proverbs 20:23"),
        ("Proverbs twenty nine verse twenty three",           "Proverbs 29:23"),
        ("Romans five and eight",                             "Romans 5:8"),
        # 'X and Y' with no book should not match (no book = no ref)
        ("chapter five and six",                              None),
        ("verse three and four",                              None),
        # Bug 1: Chapter out-of-bounds — Haggai has only 2 chapters
        ("Haggai chapter four verse five",                    None),
        ("Haggai 4",                                          None),
        ("Haggai 2 verse 3",                                  "Haggai 2:3"),
        # Bug 2: 'Second Timothy' must not be parsed as '1 Timothy 2'
        ("the epistle of the second timothy chapter two verse fifteen", "2 Timothy 2:15"),
        ("second timothy chapter two verse fifteen",          "2 Timothy 2:15"),
        # Bug 6: Quantity words — '3 things' must not produce a chapter number
        ("I have three things to tell you",                   None),
        ("there are two reasons for this",                    None),
        # Bug 7: Temporal references — 'two and a half years' must not match
        ("two and a half years",                              None),
        ("three months in the wilderness",                    None),
    ]
    tests.append(("Now Psalms one fifty says", "Psalm 150"))
    tests.append(("Psalms one fifty", "Psalm 150"))
    tests.append(("Psalm 1 verse 50", "Psalm 1:50"))
    tests.append(("John 3 16", "John 3"))  # no verse/verses/versus → chapter only
    print("-" * 70)
    print("PARSER SELF-TEST")
    print("-" * 70)
    passed = 0
    for text, expected in tests:
        result = parse_reference(text)
        ok = result == expected
        status = "[OK] " if ok else "[!!] "
        if ok:
            passed += 1
        print(f"{status} {text!r}")
        if not ok:
            print(f"   Expected : {expected!r}")
            print(f"   Got      : {result!r}")
        else:
            print(f"   -> {result}")
    
    # Bug 6: Natural language edge cases
    extra_tests = [
        ("Proverbs twenty and twenty three", "Proverbs 20:23"),
        ("chapter five and six",             None),
        ("verse three and four",             None),
        ("Proverbs twenty nine verse twenty three", "Proverbs 29:23"),
    ]
    print("\n" + "-" * 30)
    print("BUG 6 EDGE CASES")
    print("-" * 30)
    for text, expected in extra_tests:
        result = parse_reference(text)
        ok = result == expected
        status = "[PASS]" if ok else "[FAIL]"
        print(f"{status} {text!r} -> {result}")
    print(f"\n{passed}/{len(tests)} passed")
