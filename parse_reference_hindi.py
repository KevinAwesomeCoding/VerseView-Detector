# -*- coding: utf-8 -*-

import re

# ------------------- English Dictionaries (For Code-Switching) -------------------
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
ORDINAL_WORDS_ENG = {
    "first": "1", "second": "2", "third": "3", "fourth": "4", "fifth": "5",
    "sixth": "6", "seventh": "7", "eighth": "8", "ninth": "9", "tenth": "10",
    "eleventh": "11", "twelfth": "12", "thirteenth": "13", "fourteenth": "14",
    "fifteenth": "15", "sixteenth": "16", "seventeenth": "17", "eighteenth": "18",
    "nineteenth": "19", "twentieth": "20",
}

NUMBER_MAP_ENG = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}

# verse|verses|versus NOT stripped — required for chapter:verse (e.g. Psalm 1 verse 50 vs Psalm 150)
NOISE_ENG = (r"\b(let s|let us|read|the|a|an|chapter|chap|ch"
             r"|vs|forward|attention|to|now|our"
             r"|turn|open|look|see|go|pay|pages|bible|book|books"
             r"|words|word|says|said|saying|it|in|and|at|from"
             r"|today|we|will|are|is|was|back|going|return|again|of)\b")

# Verse number only when preceded by ":" or "verse"/"verses"/"versus"
REF_RE_ENG = re.compile(
    r"(?P<book>(?:[123] )?[a-z]+(?:[a-z ]+)?)"
    r"\s+"
    r"(?P<chap>\d{1,3})"
    r"(?:(?:\s*:\s*|\s+(?:verse|verses|versus)\s+)(?P<verses>\d{1,3}))?",
    re.IGNORECASE
)

# ------------------- Hindi → English book mapping -------------------
BOOKS_HI = {
    "उत्पत्ति": "Genesis", "निर्गमन": "Exodus", "लैव्यव्यवस्था": "Leviticus", "लैव्य": "Leviticus",
    "गिनती": "Numbers", "व्यवस्थाविवरण": "Deuteronomy", "व्यवस्था": "Deuteronomy",
    "यहोशू": "Joshua", "न्यायियों": "Judges", "न्यायाधीश": "Judges", "रूत": "Ruth",
    "1 शमूएल": "1 Samuel", "1शमूएल": "1 Samuel", "एक शमूएल": "1 Samuel",
    "2 शमूएल": "2 Samuel", "2शमूएल": "2 Samuel", "दो शमूएल": "2 Samuel",
    "1 राजाओं": "1 Kings", "1राजाओं": "1 Kings", "एक राजाओं": "1 Kings",
    "2 राजाओं": "2 Kings", "2राजाओं": "2 Kings", "दो राजाओं": "2 Kings",
    "1 इतिहास": "1 Chronicles", "1इतिहास": "1 Chronicles", "एक इतिहास": "1 Chronicles",
    "2 इतिहास": "2 Chronicles", "2इतिहास": "2 Chronicles", "दो इतिहास": "2 Chronicles",
    "एज्रा": "Ezra", "नहेम्याह": "Nehemiah", "एस्तेर": "Esther", "अय्यूब": "Job",
    "भजन संहिता": "Psalms", "भजन": "Psalms", "नीतिवचन": "Proverbs", "सभोपदेशक": "Ecclesiastes",
    "श्रेष्ठगीत": "Song of Solomon", "यशायाह": "Isaiah", "यशाया": "Isaiah", "यिर्मयाह": "Jeremiah",
    "यिर्मया": "Jeremiah", "विलापगीत": "Lamentations", "यहेजकेल": "Ezekiel", "दानिय्येल": "Daniel",
    "दानिएल": "Daniel", "होशे": "Hosea", "योएल": "Joel", "आमोस": "Amos", "ओबद्याह": "Obadiah",
    "योना": "Jonah", "मीका": "Micah", "नहूम": "Nahum", "हबक्कूक": "Habakkuk", "सपन्याह": "Zephaniah",
    "हाग्गै": "Haggai", "जकर्याह": "Zechariah", "मलाकी": "Malachi",
    "मत्ती": "Matthew", "मरकुस": "Mark", "लूका": "Luke", "यूहन्ना": "John",
    "प्रेरितों के काम": "Acts", "प्रेरितों": "Acts", "रोमियों": "Romans",
    "1 कुरिन्थियों": "1 Corinthians", "1कुरिन्थियों": "1 Corinthians", "एक कुरिन्थियों": "1 Corinthians",
    "2 कुरिन्थियों": "2 Corinthians", "2कुरिन्थियों": "2 Corinthians", "दो कुरिन्थियों": "2 Corinthians",
    "गलातियों": "Galatians", "इफिसियों": "Ephesians", "फिलिप्पियों": "Philippians", "कुलुस्सियों": "Colossians",
    "1 थिस्सलुनीकियों": "1 Thessalonians", "1थिस्सलुनीकियों": "1 Thessalonians", "एक थिस्सलुनीकियों": "1 Thessalonians",
    "2 थिस्सलुनीकियों": "2 Thessalonians", "2थिस्सलुनीकियों": "2 Thessalonians", "दो थिस्सलुनीकियों": "2 Thessalonians",
    "1 तीमुथियुस": "1 Timothy", "1तीमुथियुस": "1 Timothy", "एक तीमुथियुस": "1 Timothy",
    "2 तीमुथियुस": "2 Timothy", "2तीमुथियुस": "2 Timothy", "दो तीमुथियुस": "2 Timothy",
    "तीतुस": "Titus", "फिलेमोन": "Philemon", "इब्रानियों": "Hebrews", "याकूब": "James",
    "1 पतरस": "1 Peter", "1पतरस": "1 Peter", "एक पतरस": "1 Peter",
    "2 पतरस": "2 Peter", "2पतरस": "2 Peter", "दो पतरस": "2 Peter",
    "1 यूहन्ना": "1 John", "1यूहन्ना": "1 John", "एक यूहन्ना": "1 John",
    "2 यूहन्ना": "2 John", "2यूहन्ना": "2 John", "दो यूहन्ना": "2 John",
    "3 यूहन्ना": "3 John", "3यूहन्ना": "3 John", "तीन यूहन्ना": "3 John",
    "यहूदा": "Jude", "प्रकाशितवाक्य": "Revelation", "प्रकाशन": "Revelation",
}

HI_DIGITS = str.maketrans({
    "०": "0", "१": "1", "२": "2", "३": "3", "४": "4",
    "५": "5", "६": "6", "७": "7", "८": "8", "९": "9"
})

NUMBER_MAP_HI = {
    "एक": "1", "दो": "2", "तीन": "3", "चार": "4", "पाँच": "5", "पांच": "5",
    "छः": "6", "छह": "6", "सात": "7", "आठ": "8", "नौ": "9", "दस": "10",
    "ग्यारह": "11", "बारह": "12", "तेरह": "13", "चौदह": "14", "पन्द्रह": "15",
    "सोलह": "16", "सत्रह": "17", "अठारह": "18", "उन्नीस": "19", "बीस": "20",
    "इक्कीस": "21", "बाईस": "22", "तेईस": "23", "चौबीस": "24", "पच्चीस": "25",
    "छब्बीस": "26", "सत्ताईस": "27", "अट्ठाईस": "28", "उनतीस": "29", "तीस": "30",
    "चालीस": "40", "पचास": "50", "साठ": "60", "सत्तर": "70", "अस्सी": "80", "नब्बे": "90", "सौ": "100"
}

# Hindi "one fifty" → 150 (same idea as English): ones 1–9 + tens 20–90 → one number
HI_ONES_TENS = (
    (("एक", 1), ("दो", 2), ("तीन", 3), ("चार", 4), ("पाँच", 5), ("पांच", 5),
     ("छः", 6), ("छह", 6), ("सात", 7), ("आठ", 8), ("नौ", 9)),
    (("बीस", 20), ("तीस", 30), ("चालीस", 40), ("पचास", 50), ("साठ", 60),
     ("सत्तर", 70), ("अस्सी", 80), ("नब्बे", 90)),
)

BOOK_FILLERS_HI = ["अध्याय", "वचन", "पद"]

# ------------------- English Math & Resolver -------------------
def convert_word_numbers_eng(text):
    text = text.replace("-", " ")
    words = text.split()
    result = []
    i = 0
    while i < len(words):
        w = words[i]
        if i + 1 < len(words) and w in NUMBER_MAP_ENG and words[i + 1] == "hundred":
            base = int(NUMBER_MAP_ENG[w]) * 100
            if i + 2 < len(words) and words[i + 2] in NUMBER_MAP_ENG:
                result.append(str(base + int(NUMBER_MAP_ENG[words[i + 2]])))
                i += 3
            else:
                result.append(str(base))
                i += 2
            continue
        # "one fifty" → 150 (same as English parser)
        if i + 1 < len(words) and w in NUMBER_MAP_ENG and words[i + 1] in NUMBER_MAP_ENG:
            fv = int(NUMBER_MAP_ENG[w])
            sv = int(NUMBER_MAP_ENG[words[i + 1]])
            if 1 <= fv <= 9 and sv >= 20 and sv % 10 == 0:
                combined = fv * 100 + sv
                if i + 2 < len(words) and words[i + 2] in NUMBER_MAP_ENG:
                    third = int(NUMBER_MAP_ENG[words[i + 2]])
                    if 1 <= third <= 9:
                        combined += third
                        i += 3
                        result.append(str(combined))
                        continue
                i += 2
                result.append(str(combined))
                continue
        if i + 1 < len(words) and w in NUMBER_MAP_ENG and words[i + 1] in NUMBER_MAP_ENG:
            fv = int(NUMBER_MAP_ENG[w])
            sv = int(NUMBER_MAP_ENG[words[i + 1]])
            if fv >= 20 and fv % 10 == 0 and 1 <= sv <= 9:
                result.append(str(fv + sv))
                i += 2
                continue
        result.append(str(NUMBER_MAP_ENG[w]) if w in NUMBER_MAP_ENG else w)
        i += 1
    return " ".join(result)

def resolve_book_eng(bookraw: str):
    b = bookraw.strip().lower()
    if b in BOOKS_ENG:
        return BOOKS_ENG[b]
    if len(b) >= 4:
        for key in BOOKS_ENG:
            if key in b or b in key:
                return BOOKS_ENG[key]
    return None

# ------------------- Hindi Normalizers -------------------
def normalize_digits_hi(s: str) -> str:
    return s.translate(HI_DIGITS)

def normalize_number_words_hi(s: str) -> str:
    # First: "एक पचास" → 150, "दो साठ" → 260, etc. (same as English "one fifty" → 150)
    for (one_word, one_val), (ten_word, ten_val) in (
        (o, t) for o in HI_ONES_TENS[0] for t in HI_ONES_TENS[1]
    ):
        s = s.replace(one_word + " " + ten_word, str(one_val * 100 + ten_val))
    for k in sorted(NUMBER_MAP_HI.keys(), key=len, reverse=True):
        s = s.replace(k, NUMBER_MAP_HI[k])
    s = re.sub(
        r'\b(20|30|40|50|60|70|80|90)\s+([1-9])\b',
        lambda m: str(int(m.group(1)) + int(m.group(2))),
        s
    )
    return s

def normalize_numbers_only(s: str) -> str:
    """Combined Normalizer: English numbers first, then Hindi numbers."""
    s = s.lower()
    for word, num in ORDINAL_WORDS_ENG.items():
        s = re.sub(rf"\b{word}\b", num, s)
    s = convert_word_numbers_eng(s)
    s = normalize_digits_hi(s)
    s = re.sub(r"[।\.,!?;:\-–]", " ", s)
    s = normalize_number_words_hi(s)
    return " ".join(s.split())

# ------------------- Main Code-Switched Parser -------------------
def parse_references(text: str):
    if not text:
        return []
    results = []
    t = text.lower()
    for word, num in ORDINAL_WORDS_ENG.items():
        t = re.sub(rf"\b{word}\b", num, t)
    t = convert_word_numbers_eng(t)
    t = normalize_digits_hi(t)
    t = normalize_number_words_hi(t)

    # 1. English Parser Pipeline
    t_eng = re.sub(r"[^a-z0-9 ]", " ", t)
    t_eng = re.sub(NOISE_ENG, " ", t_eng)
    t_eng = " ".join(t_eng.split())
    for m in REF_RE_ENG.finditer(t_eng):
        eng = resolve_book_eng(m.group("book"))
        if eng:
            results.append(f"{eng} {m.group('chap')}{(':' + m.group('verses')) if m.group('verses') else ''}")
    if results:
        return results

    # 2. Hindi Parser Pipeline (verse only when : or वचन/पद before verse number, same as English)
    for hi_book in sorted(BOOKS_HI.keys(), key=len, reverse=True):
        if hi_book in t:
            eng_book = BOOKS_HI[hi_book]
            idx = t.index(hi_book)
            after_raw = t[idx + len(hi_book):].strip()
            after = after_raw
            for filler in BOOK_FILLERS_HI:
                after = after.replace(filler, "").strip()
            after = re.sub(NOISE_ENG, " ", after).strip()
            # chapter:verse only when explicit : - । or वचन/पद between numbers
            m = re.search(r'(\d{1,3})\s*[:\-।]\s*(\d{1,3})', after)
            if m:
                results.append(f"{eng_book} {m.group(1)}:{m.group(2)}")
                continue
            m2 = re.search(r'(\d{1,3})\s*(?:वचन|पद)\s*(\d{1,3})', after_raw)
            if m2:
                results.append(f"{eng_book} {m2.group(1)}:{m2.group(2)}")
                continue
            # single number → chapter only (e.g. भजन 150)
            m3 = re.search(r'(\d{1,3})', after)
            if m3:
                results.append(f"{eng_book} {m3.group(1)}")
                continue
    return results

def parse_reference(text: str) -> str | None:
    refs = parse_references(text)
    return refs[0] if refs else None

# ── Verse-Jump Parser ──────────────────────────────────────────────────────────
# Hindi verse-jump keywords (वचन = verse/word, पद = verse/step)
_VERSE_JUMP_RE = re.compile(
    r'\b(\d{1,3})\s*(?:st|nd|rd|th)?\s+verse\b'
    r'|\bverse\s+(\d{1,3})\b',
    re.IGNORECASE
)
_VERSE_JUMP_RE_HI = re.compile(
    r'(\d{1,3})\s*(?:वें|वाँ|वां|वा)?\s*(?:वचन|पद)'  # "3 वचन", "3वें पद"
    r'|(?:वचन|पद)\s+(\d{1,3})',                         # "वचन 3"
)

def parse_verse_jump(text: str) -> int | None:
    """
    Detects verse navigation like "go back to the first verse", "third verse",
    "3 वचन", "पद 5". Returns verse int or None.
    The caller (master.py) applies current_book + current_chapter context.
    """
    if not text:
        return None
    t = text.lower()
    for word, num in ORDINAL_WORDS_ENG.items():
        t = re.sub(rf"\b{word}\b", num, t)
    t = convert_word_numbers_eng(t)
    t = normalize_digits_hi(t)
    t = normalize_number_words_hi(t)

    # English: "verse 3", "3rd verse"
    m = _VERSE_JUMP_RE.search(t)
    if m:
        val = m.group(1) or m.group(2)
        if val:
            return int(val)

    # Hindi: "3 वचन", "वचन 5", "पद 3"
    m = _VERSE_JUMP_RE_HI.search(t)
    if m:
        val = m.group(1) or m.group(2)
        if val:
            return int(val)

    return None
