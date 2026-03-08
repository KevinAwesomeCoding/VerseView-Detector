import re

BOOKS_ENG = {
    "genesis": "Genesis", "exodus": "Exodus", "leviticus": "Leviticus",
    "numbers": "Numbers", "deuteronomy": "Deuteronomy", "joshua": "Joshua",
    "judges": "Judges", "ruth": "Ruth",
    "1 samuel": "1 Samuel", "first samuel": "1 Samuel", "one samuel": "1 Samuel",
    "2 samuel": "2 Samuel", "second samuel": "2 Samuel", "two samuel": "2 Samuel",
    "1 kings": "1 Kings", "first kings": "1 Kings", "one kings": "1 Kings",
    "2 kings": "2 Kings", "second kings": "2 Kings", "two kings": "2 Kings",
    "1 chronicles": "1 Chronicles", "first chronicles": "1 Chronicles",
    "2 chronicles": "2 Chronicles", "second chronicles": "2 Chronicles",
    "ezra": "Ezra", "nehemiah": "Nehemiah", "esther": "Esther", "job": "Job",
    "psalm": "Psalm", "psalms": "Psalm", "proverbs": "Proverbs",
    "ecclesiastes": "Ecclesiastes",
    "song of solomon": "Song of Solomon", "songs of solomon": "Song of Solomon",
    "isaiah": "Isaiah", "jeremiah": "Jeremiah", "lamentations": "Lamentations",
    "ezekiel": "Ezekiel", "daniel": "Daniel", "hosea": "Hosea", "joel": "Joel",
    "amos": "Amos", "obadiah": "Obadiah", "jonah": "Jonah", "micah": "Micah",
    "nahum": "Nahum", "habakkuk": "Habakkuk", "zephaniah": "Zephaniah",
    "haggai": "Haggai", "zechariah": "Zechariah", "malachi": "Malachi",
    "matthew": "Matthew", "mark": "Mark", "luke": "Luke", "john": "John",
    "acts": "Acts", "romans": "Romans",
    "1 corinthians": "1 Corinthians", "first corinthians": "1 Corinthians", "one corinthians": "1 Corinthians",
    "2 corinthians": "2 Corinthians", "second corinthians": "2 Corinthians", "two corinthians": "2 Corinthians",
    "galatians": "Galatians", "ephesians": "Ephesians", "philippians": "Philippians",
    "colossians": "Colossians",
    "1 thessalonians": "1 Thessalonians", "first thessalonians": "1 Thessalonians", "one thessalonians": "1 Thessalonians",
    "2 thessalonians": "2 Thessalonians", "second thessalonians": "2 Thessalonians", "two thessalonians": "2 Thessalonians",
    "1 timothy": "1 Timothy", "first timothy": "1 Timothy", "one timothy": "1 Timothy",
    "2 timothy": "2 Timothy", "second timothy": "2 Timothy", "two timothy": "2 Timothy",
    "titus": "Titus", "philemon": "Philemon", "hebrews": "Hebrews", "james": "James",
    "1 peter": "1 Peter", "first peter": "1 Peter", "one peter": "1 Peter",
    "2 peter": "2 Peter", "second peter": "2 Peter", "two peter": "2 Peter",
    "1 john": "1 John", "first john": "1 John", "one john": "1 John",
    "2 john": "2 John", "second john": "2 John", "two john": "2 John",
    "3 john": "3 John", "third john": "3 John", "three john": "3 John",
    "jude": "Jude", "revelation": "Revelation", "revelations": "Revelation",
}

# ── EXPANDED: fourth–twentieth for verse-jump phrases ──
ORDINAL_WORDS = {
    "first": "1", "second": "2", "third": "3", "fourth": "4", "fifth": "5",
    "sixth": "6", "seventh": "7", "eighth": "8", "ninth": "9", "tenth": "10",
    "eleventh": "11", "twelfth": "12", "thirteenth": "13", "fourteenth": "14",
    "fifteenth": "15", "sixteenth": "16", "seventeenth": "17", "eighteenth": "18",
    "nineteenth": "19", "twentieth": "20",
}

NUMBER_MAP = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}

def convert_word_numbers(text):
    text = text.replace("-", " ")
    words = text.split()
    result = []
    i = 0
    while i < len(words):
        w = words[i]
        if i + 1 < len(words) and w in NUMBER_MAP and words[i + 1] == "hundred":
            base = int(NUMBER_MAP[w]) * 100
            if i + 2 < len(words) and words[i + 2] in NUMBER_MAP:
                result.append(str(base + int(NUMBER_MAP[words[i + 2]])))
                i += 3
            else:
                result.append(str(base))
                i += 2
            continue
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

def normalize_text(s: str) -> str:
    s = s.lower()
    for word, num in ORDINAL_WORDS.items():
        s = re.sub(rf"\b{word}\b", num, s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = convert_word_numbers(s)
    noise = (r"\b(let s|let us|read|the|a|an|chapter|chap|ch"
             r"|verse|verses|versus|vs|forward|attention|to|now|our"
             r"|turn|open|look|see|go|pay|pages|bible|book|books"
             r"|words|word|says|said|saying|it|in|and|at|from"
             r"|today|we|will|are|is|was|back|going|return|again|of)\b")
    s = re.sub(noise, " ", s)
    return " ".join(s.split())

def normalize_numbers_only(s: str) -> str:
    s = s.lower()
    for word, num in ORDINAL_WORDS.items():
        s = re.sub(rf"\b{word}\b", num, s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = convert_word_numbers(s)
    return " ".join(s.split())

def resolve_book(bookraw: str):
    b = bookraw.strip().lower()
    if b in BOOKS_ENG:
        return BOOKS_ENG[b]
    if len(b) >= 4:
        for key in BOOKS_ENG:
            if key in b or b in key:
                return BOOKS_ENG[key]
    return None

REF_RE = re.compile(
    r"(?P<book>(?:[123] )?[a-z]+(?:[a-z ]+)?)"
    r"\s+"
    r"(?P<chap>\d{1,3})"
    r"(?:[:\s]+"
    r"(?P<verses>\d{1,3}))?",
    re.IGNORECASE
)

def parse_references(text: str):
    if not text:
        return []
    results = []
    t = normalize_text(text)
    for m in REF_RE.finditer(t):
        eng = resolve_book(m.group("book"))
        if eng:
            results.append(f"{eng} {m.group('chap')}{(':' + m.group('verses')) if m.group('verses') else ''}")
    return results

def parse_reference(text: str):
    refs = parse_references(text)
    return refs[0] if refs else None

# ── Verse-Jump Parser ──────────────────────────────────────────────────────────
# Detects standalone verse navigation: "go back to the first verse", "verse five",
# "third verse", etc. Returns just the verse int. Use alongside parse_references()
# to handle mid-sermon redirections. The CALLER (master) applies the current context.

_VERSE_JUMP_RE = re.compile(
    r'\b(\d{1,3})\s*(?:st|nd|rd|th)?\s+verse\b'   # "3rd verse", "3 verse"
    r'|\bverse\s+(\d{1,3})\b',                      # "verse 3"
    re.IGNORECASE
)

def parse_verse_jump(text: str) -> int | None:
    """
    Detects verse navigation phrases like:
      "go back to the first verse"  → 1
      "when we go to the third verse" → 3
      "let's read verse five"        → 5
      "back to verse twelve"         → 12

    Returns verse number as int, or None if not found.
    Requires context (book + chapter) from the caller (master.py) to build full ref.
    """
    if not text:
        return None
    t = text.lower()
    for word, num in ORDINAL_WORDS.items():
        t = re.sub(rf"\b{word}\b", num, t)
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    t = convert_word_numbers(t)
    m = _VERSE_JUMP_RE.search(t)
    if m:
        val = m.group(1) or m.group(2)
        if val:
            return int(val)
    return None


if __name__ == "__main__":
    tests = [
        ("We're seventeen to nineteen", None),
        ("Turn with me to the book of Daniel chapter two", "Daniel 2"),
        ("Let us read Romans chapter one verses five", "Romans 1:5"),
        ("John three seventeen", "John 3:17"),
        ("First Corinthians thirteen four", "1 Corinthians 13:4"),
        ("Isaiah fifty four six", "Isaiah 54:6"),
    ]
    jump_tests = [
        ("let's go back to the first verse", 1),
        ("when we go to the third verse", 3),
        ("verse five", 5),
        ("back to verse twelve", 12),
        ("going back to the seventh verse", 7),
    ]
    print("─" * 60)
    for s, expected in tests:
        result = parse_reference(s)
        ok = "✅" if result == expected else "❌"
        print(f"{ok} '{s}' → {result}")
    print("─" * 60)
    for s, expected in jump_tests:
        result = parse_verse_jump(s)
        ok = "✅" if result == expected else "❌"
        print(f"{ok} '{s}' → {result}")
