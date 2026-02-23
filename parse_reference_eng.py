# parse_reference_eng.py

import re

BOOKS_ENG = {
    "genesis": "Genesis", "exodus": "Exodus", "leviticus": "Leviticus",
    "numbers": "Numbers", "deuteronomy": "Deuteronomy",
    "joshua": "Joshua", "judges": "Judges", "ruth": "Ruth",
    "1 samuel": "1 Samuel", "first samuel": "1 Samuel", "one samuel": "1 Samuel",
    "2 samuel": "2 Samuel", "second samuel": "2 Samuel", "two samuel": "2 Samuel",
    "1 kings": "1 Kings", "first kings": "1 Kings", "one kings": "1 Kings",
    "2 kings": "2 Kings", "second kings": "2 Kings", "two kings": "2 Kings",
    "1 chronicles": "1 Chronicles", "first chronicles": "1 Chronicles",
    "2 chronicles": "2 Chronicles", "second chronicles": "2 Chronicles",
    "ezra": "Ezra", "nehemiah": "Nehemiah", "esther": "Esther", "job": "Job",
    "psalm": "Psalm", "psalms": "Psalm",
    "proverbs": "Proverbs", "ecclesiastes": "Ecclesiastes",
    "song of solomon": "Song of Solomon", "songs of solomon": "Song of Solomon",
    "isaiah": "Isaiah", "jeremiah": "Jeremiah", "lamentations": "Lamentations",
    "ezekiel": "Ezekiel", "daniel": "Daniel",
    "hosea": "Hosea", "joel": "Joel", "amos": "Amos", "obadiah": "Obadiah",
    "jonah": "Jonah", "micah": "Micah", "nahum": "Nahum", "habakkuk": "Habakkuk",
    "zephaniah": "Zephaniah", "haggai": "Haggai",
    "zechariah": "Zechariah", "malachi": "Malachi",
    "matthew": "Matthew", "mark": "Mark", "luke": "Luke", "john": "John",
    "acts": "Acts", "romans": "Romans",
    "1 corinthians": "1 Corinthians", "first corinthians": "1 Corinthians", "one corinthians": "1 Corinthians",
    "2 corinthians": "2 Corinthians", "second corinthians": "2 Corinthians", "two corinthians": "2 Corinthians",
    "galatians": "Galatians", "ephesians": "Ephesians",
    "philippians": "Philippians", "colossians": "Colossians",
    "1 thessalonians": "1 Thessalonians", "first thessalonians": "1 Thessalonians", "one thessalonians": "1 Thessalonians",
    "2 thessalonians": "2 Thessalonians", "second thessalonians": "2 Thessalonians", "two thessalonians": "2 Thessalonians",
    "1 timothy": "1 Timothy", "first timothy": "1 Timothy", "one timothy": "1 Timothy",
    "2 timothy": "2 Timothy", "second timothy": "2 Timothy", "two timothy": "2 Timothy",
    "titus": "Titus", "philemon": "Philemon", "hebrews": "Hebrews",
    "james": "James",
    "1 peter": "1 Peter", "first peter": "1 Peter", "one peter": "1 Peter",
    "2 peter": "2 Peter", "second peter": "2 Peter", "two peter": "2 Peter",
    "1 john": "1 John", "first john": "1 John", "one john": "1 John",
    "2 john": "2 John", "second john": "2 John", "two john": "2 John",
    "3 john": "3 John", "third john": "3 John", "three john": "3 John",
    "jude": "Jude",
    "revelation": "Revelation", "revelations": "Revelation",
}

ORDINAL_WORDS = {"first": "1", "second": "2", "third": "3"}

NUMBER_MAP = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13",
    "fourteen": "14", "fifteen": "15", "sixteen": "16", "seventeen": "17",
    "eighteen": "18", "nineteen": "19",
    "twenty": "20", "thirty": "30", "forty": "40", "fifty": "50",
    "sixty": "60", "seventy": "70", "eighty": "80", "ninety": "90",
}


def convert_word_numbers(text):
    """Convert number words to digits, handles compounds and hundreds."""
    text = text.replace("-", " ")
    parts = text.split(":")
    converted_parts = []
    for part in parts:
        words = part.split()
        result = []
        i = 0
        while i < len(words):
            w = words[i]
            # "one hundred X" pattern
            if i + 1 < len(words) and w in NUMBER_MAP and words[i + 1] == "hundred":
                base = int(NUMBER_MAP[w]) * 100
                if i + 2 < len(words) and words[i + 2] in NUMBER_MAP:
                    result.append(str(base + int(NUMBER_MAP[words[i + 2]])))
                    i += 3
                else:
                    result.append(str(base))
                    i += 2
                continue
            # Compound: "twenty three" → 23
            if i + 1 < len(words) and w in NUMBER_MAP and words[i + 1] in NUMBER_MAP:
                fv = int(NUMBER_MAP[w])
                sv = int(NUMBER_MAP[words[i + 1]])
                if fv >= 20 and fv % 10 == 0 and 1 <= sv <= 9:
                    result.append(str(fv + sv))
                    i += 2
                    continue
            # Single word number
            result.append(NUMBER_MAP[w] if w in NUMBER_MAP else w)
            i += 1
        converted_parts.append(" ".join(result))
    return ":".join(converted_parts)


def normalize_text(s: str) -> str:
    """
    Full normalization for the main parser.
    Strips ALL filler words including 'verse', 'to', 'through' etc.
    Result: bare 'Book Chapter Verse' string for regex matching.
    """
    s = s.lower()
    # Step 1: ordinals
    for word, num in ORDINAL_WORDS.items():
        s = re.sub(r"\b" + word + r"\b", num, s)
    # Step 2: strip punctuation FIRST so "five." → "five" before conversion
    s = re.sub(r"[^a-z0-9:\s]", " ", s)
    # Step 3: convert word numbers
    s = convert_word_numbers(s)
    # Step 4: strip all filler/connector words
    noise = (
        r"\b(let\'s|lets|let|us|read|the|a|an|chapter|chap|ch|"
        r"verse|verses|versus|v|forward|attention|to|now|our|"
        r"turn|open|look|see|go|pay|pages|bible|book|books|"
        r"words|word|says|said|saying|it|in|and|at|from|"
        r"today|we|will|are|is|was)\b"
    )
    s = re.sub(noise, " ", s)
    return " ".join(s.split())


def normalize_numbers_only(s: str) -> str:
    """
    Light normalization — converts word numbers and strips punctuation
    BUT keeps connector/keyword words like 'verse', 'to', 'through', 'and'.
    Used for range detection and contextual cross-line detection ONLY.
    """
    s = s.lower()
    # Step 1: ordinals
    for word, num in ORDINAL_WORDS.items():
        s = re.sub(r"\b" + word + r"\b", num, s)
    # Step 2: strip punctuation
    s = re.sub(r"[^a-z0-9:\s]", " ", s)
    # Step 3: convert word numbers
    s = convert_word_numbers(s)
    return " ".join(s.split())


def resolve_book(book_raw: str):
    """Find the canonical book name from raw matched text."""
    b = book_raw.strip().lower()
    if b in BOOKS_ENG:
        return BOOKS_ENG[b]
    for key in BOOKS_ENG:
        if key in b or b in key:
            return BOOKS_ENG[key]
    return None


REF_RE = re.compile(
    r"(?P<book>(?:[1-3]\s+)?[a-z]+(?:\s+[a-z]+)*?)"
    r"\s+"
    r"(?P<chap>\d{1,3})"
    r"(?:\s*[:]\s*|\s+)"
    r"(?P<verses>\d{1,3})",
    re.IGNORECASE
)


def parse_references(text: str):
    """Parse all verse references. Returns list of 'Book Ch:V' strings."""
    if not text:
        return []
    results = []
    t = normalize_text(text)
    for m in REF_RE.finditer(t):
        eng = resolve_book(m.group("book"))
        if eng:
            results.append(f"{eng} {m.group('chap')}:{m.group('verses')}")
    return results


def parse_reference(text: str):
    """Parse the first verse reference in text."""
    refs = parse_references(text)
    return refs[0] if refs else None


if __name__ == "__main__":
    tests = [
        "Let us read Romans chapter one verses five",
        "Let us read Romans chapter one verses five.",
        "Forward our attention to John three seventeen",
        "Now let's forward our attention to one Corinthians five:one",
        "Romans eight twenty-eight",
        "First Corinthians thirteen:four",
        "Isaiah fifty four six",
        "Mark five versus six",
        "Mark five verses six.",
        "Turn your Bible to Job twenty two",
        "Let's turn our pages to Philippians four words six",
        "Matthew five verses four.",
        "Now let us pay attention to Matthew five verses six.",
    ]

    print("=" * 70)
    print("PARSER TEST")
    print("=" * 70)
    for s in tests:
        result = parse_references(s)
        norm_full = normalize_text(s)
        norm_light = normalize_numbers_only(s)
        status = "✅" if result else "❌"
        print(f"{status} {s}")
        print(f"   normalize_text        : {norm_full}")
        print(f"   normalize_numbers_only: {norm_light}")
        print(f"   Result                : {result}\n")
