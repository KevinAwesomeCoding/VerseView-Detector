# -*- coding: utf-8 -*-
import re

# ── BOOK ALIASES ──
# Covers: canonical names, common ASR mishearings, misspellings,
# alternate names (Song of Songs / Canticles), phonetic Indian-English variants.
BOOKS_ENG = {
    # ── Old Testament ──
    "genesis": "Genesis",
    "exodus": "Exodus",
    "leviticus": "Leviticus",
    "numbers": "Numbers",
    "deuteronomy": "Deuteronomy", "deutronomy": "Deuteronomy", "deutronmy": "Deuteronomy",
    "joshua": "Joshua",
    "judges": "Judges",
    "ruth": "Ruth",
    "1 samuel": "1 Samuel",   "first samuel": "1 Samuel",
    "2 samuel": "2 Samuel",   "second samuel": "2 Samuel",
    "1 kings": "1 Kings",     "first kings": "1 Kings",
    "2 kings": "2 Kings",     "second kings": "2 Kings",
    "1 chronicles": "1 Chronicles", "first chronicles": "1 Chronicles",
    "2 chronicles": "2 Chronicles", "second chronicles": "2 Chronicles",
    "ezra": "Ezra",
    "nehemiah": "Nehemiah", "nehemia": "Nehemiah", "nehimia": "Nehemiah",
    "esther": "Esther",
    "job": "Job",
    "psalm": "Psalm", "psalms": "Psalm",
    # ASR phonetic: Indian preachers → "Psalms" is heard as "Sam's"
    "sams": "Psalm", "sam s": "Psalm",
    "proverbs": "Proverbs",
    "ecclesiastes": "Ecclesiastes", "ecclesiast": "Ecclesiastes",
    # Song of Solomon — all common names/abbreviations
    "song of solomon":  "Song of Solomon",
    "songs of solomon": "Song of Solomon",
    "song of songs":    "Song of Solomon",
    "song of song":     "Song of Solomon",
    "song songs":       "Song of Solomon",   # "of" sometimes dropped in speech
    "canticles":        "Song of Solomon",
    "sos":              "Song of Solomon",
    "isaiah": "Isaiah", "isaia": "Isaiah", "isaya": "Isaiah",
    "jeremiah": "Jeremiah",
    "lamentations": "Lamentations",
    "ezekiel": "Ezekiel", "ezakiel": "Ezekiel", "ezekeal": "Ezekiel",
    "daniel": "Daniel",
    "hosea": "Hosea",
    "joel": "Joel",
    "amos": "Amos",
    "obadiah": "Obadiah",
    "jonah": "Jonah",
    "micah": "Micah",
    "nahum": "Nahum",
    "habakkuk": "Habakkuk", "habakuk": "Habakkuk",
    "zephaniah": "Zephaniah",
    "haggai": "Haggai",
    "zechariah": "Zechariah", "zecharia": "Zechariah",
    "malachi": "Malachi",
    # ── New Testament ──
    "matthew": "Matthew",
    "mark": "Mark",
    "luke": "Luke",
    "john": "John",
    "acts": "Acts",
    "romans": "Romans",
    "1 corinthians": "1 Corinthians", "first corinthians": "1 Corinthians",
    "corinthians": "1 Corinthians",   # bare → assume 1st
    "2 corinthians": "2 Corinthians", "second corinthians": "2 Corinthians",
    "galatians": "Galatians",
    "ephesians": "Ephesians",
    "philippians": "Philippians", "phillipians": "Philippians",
    "colossians": "Colossians",
    "1 thessalonians": "1 Thessalonians", "first thessalonians": "1 Thessalonians",
    "2 thessalonians": "2 Thessalonians", "second thessalonians": "2 Thessalonians",
    "thessalonians": "1 Thessalonians",
    "1 timothy": "1 Timothy", "first timothy": "1 Timothy",
    "2 timothy": "2 Timothy", "second timothy": "2 Timothy",
    "timothy": "1 Timothy",
    "titus": "Titus",
    "philemon": "Philemon",
    "hebrews": "Hebrews",
    "james": "James",
    "1 peter": "1 Peter",  "first peter": "1 Peter",
    "2 peter": "2 Peter",  "second peter": "2 Peter",
    "1 john": "1 John",    "first john": "1 John",
    "2 john": "2 John",    "second john": "2 John",
    "3 john": "3 John",    "third john": "3 John",
    "jude": "Jude",
    "revelation": "Revelation", "revelations": "Revelation",
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
    """Convert spoken numbers to digits: "twenty five" → "25", "two hundred three" → "203"."""
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


def normalize_text(s: str) -> str:
    """Full normalization: lowercase, ordinal conversion, number conversion, noise removal."""
    s = s.lower()
    # Only replace "first/second/third" — NOT one/two/three (would break "twenty two" etc.)
    for word, num in ORDINAL_WORDS.items():
        s = re.sub(rf"\b{word}\b", num, s)
    # Strip punctuation/special chars → space
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    # Convert spoken numbers to digits
    s = convert_word_numbers(s)
    # Remove sermon filler / navigation words
    # NOTE: "of" is intentionally NOT stripped — needed for "Song of Songs", "Song of Solomon"
    noise = (
        r"\b(lets|let s|let us|read|the|a|an|chapter|chap|ch"
        r"|verse|verses|versus|vs|forward|attention|to|now|our"
        r"|turn|open|look|see|go|pay|pages|bible|book|books"
        r"|words|word|says|said|saying|it|in|and|at|from"
        r"|today|we|will|are|is|was)\b"
    )
    s = re.sub(noise, " ", s)
    return " ".join(s.split())


def normalize_numbers_only(s: str) -> str:
    """Convert word numbers to digits only — no noise stripping (used for range detection)."""
    s = s.lower()
    for word, num in ORDINAL_WORDS.items():
        s = re.sub(rf"\b{word}\b", num, s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = convert_word_numbers(s)
    return " ".join(s.split())


def resolve_book(bookraw: str):
    """Return canonical book name or None. Uses word-boundary matching to avoid false positives."""
    b = bookraw.strip().lower()
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
REF_RE = re.compile(
    r"(?P<book>(?:[123] )?[a-z]+(?:[a-z ]+)?)"
    r"\s+"
    r"(?P<chap>\d{1,3})"
    r"(?:[:\s]+"
    r"(?P<verses>\d{1,3}))?",
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
            ref = f"{eng} {m.group('chap')}"
            if m.group("verses"):
                ref += f":{m.group('verses')}"
            results.append(ref)
    return results


def parse_reference(text: str):
    refs = parse_references(text)
    return refs[0] if refs else None


# ── Self-test ──
if __name__ == "__main__":
    tests = [
        ("Turn to Romans chapter eight verse twenty eight",   "Romans 8:28"),
        ("John three sixteen",                                "John 3:16"),
        ("First Corinthians thirteen four",                   "1 Corinthians 13:4"),
        ("Isaiah fifty four six",                             "Isaiah 54:6"),
        ("Acts thirteen verse two",                           "Acts 13:2"),
        ("Let us read John one verses five",                  "John 1:5"),
        ("Jeremiah chapter nine verse one",                   "Jeremiah 9:1"),
        ("Jeremiah chapter twenty verse nine",                "Jeremiah 20:9"),
        # Phonetic / ASR
        ("Turn with me to Sam's nine",                        "Psalm 9"),
        ("Sam's Nayan verse one",                             "Psalm 9:1"),
        ("Sam's Nayan one to ten",                            "Psalm 9:1"),
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
    ]
    print("-" * 70)
    print("PARSER SELF-TEST")
    print("-" * 70)
    passed = 0
    for text, expected in tests:
        result = parse_reference(text)
        ok = result == expected
        status = "✅" if ok else "❌"
        if ok:
            passed += 1
        print(f"{status} {text!r}")
        if not ok:
            print(f"   Expected : {expected!r}")
            print(f"   Got      : {result!r}")
        else:
            print(f"   → {result}")
    print(f"\n{passed}/{len(tests)} passed")
