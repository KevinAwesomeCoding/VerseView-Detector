# -*- coding: utf-8 -*-
import re
import unicodedata

# ------------------- Malayalam → English book mapping -------------------
BOOKS = {
    # OT
    "ഉല്പത്തി": "Genesis",
    "പുറപ്പാട്": "Exodus",
    "ലേവ്യപുസ്തകം": "Leviticus",
    "ലേവ്യ": "Leviticus",
    "ലേവ്യപു": "Leviticus",
    "സംഖ്യാപുസ്തകം": "Numbers",
    "സംഖ്യ": "Numbers",
    "ആവർത്തനം": "Deuteronomy",
    "യോശുവ": "Joshua",
    "ന്യായാധിപന്മാർ": "Judges",
    "റൂത്ത്": "Ruth",
    "രൂത്ത്": "Ruth",
    # Numbered OT
    "1 ശമുവേൽ": "1 Samuel",
    "1ശമൂവേൽ": "1 Samuel",
    "ഒന്ന് ശമൂവേൽ": "1 Samuel",
    "2 ശമൂവേൽ": "2 Samuel",
    "2ശമൂവേൽ": "2 Samuel",
    "രണ്ട് ശമൂവേൽ": "2 Samuel",
    "1 രാജാ": "1 Kings",
    "ഒന്നു രാജ്": "1 Kings",
    "ഒന്ന് രാജാ": "1 Kings",
    "1 രാജാക്കന്മാർ": "1 Kings",
    "1രാജാക്കന്മാർ": "1 Kings",
    "ഒന്ന് രാജാക്കന്മാർ": "1 Kings",
    "2 രാജാ": "2 Kings",
    "രണ്ടു രാജ്": "2 Kings",
    "രണ്ട് രാജാ": "2 Kings",
    "2 രാജാക്കന്മാർ": "2 Kings",
    "2രാജാക്കന്മാർ": "2 Kings",
    "രണ്ട് രാജാക്കന്മാർ": "2 Kings",
    "1 ദിനവൃത്താന്തം": "1 Chronicles",
    "1ദിനവൃത്താന്തം": "1 Chronicles",
    "ഒന്ന് ദിനവൃത്താന്തം": "1 Chronicles",
    "2 ദിനവൃത്താന്തം": "2 Chronicles",
    "2ദിനവൃത്താന്തം": "2 Chronicles",
    "രണ്ട് ദിനവൃത്താന്തം": "2 Chronicles",
    "1 ദിനവൃത്താന്തങ്ങൾ": "1 Chronicles",
    "1ദിനവൃത്താന്തങ്ങൾ": "1 Chronicles",
    "ഒന്ന് ദിനവൃത്താന്തങ്ങൾ": "1 Chronicles",
    "2 ദിനവൃത്താന്തങ്ങൾ": "2 Chronicles",
    "2ദിനവൃത്താന്തങ്ങൾ": "2 Chronicles",
    "രണ്ട് ദിനവൃത്താന്തങ്ങൾ": "2 Chronicles",
    # More OT
    "എസ്രാ": "Ezra",
    "എസ്ര": "Ezra",
    "നെഹെമ്യാവു": "Nehemiah",
    "നെഹെമ്യാ": "Nehemiah",
    "നെഹമിയ": "Nehemiah",
    "എസ്തേർ": "Esther",
    "എസ്ഥേർ": "Esther",
    "ഇയ്യോബ്": "Job",
    "സങ്കീർത്തനങ്ങൾ": "Psalms",
    "സങ്കീർത്തനം": "Psalms",
    "സദൃശ്യവാക്യങ്ങൾ": "Proverbs",
    "സദൃശ്യവാക്യം": "Proverbs",
    "സദൃശ്യം": "Proverbs",
    "സഭാപ്രസംഗി": "Ecclesiastes",
    "പ്രസംഗി": "Ecclesiastes",
    "ഉത്തമഗീതം": "Song of Solomon",
    "പരമഗീതം": "Song of Solomon",
    "യെശയ്യാവ്": "Isaiah",
    "യെശയ്യാ": "Isaiah",
    "ഏഷ്യാ": "Isaiah",
    "യിരെമ്യാവ്": "Jeremiah",
    "ഇര മ്യാവൂ": "Jeremiah",
    "യിരെമ്യാ": "Jeremiah",
    "വിലാപങ്ങൾ": "Lamentations",
    "വിലാപം": "Lamentations",
    "യെഹെസ്കേൽ": "Ezekiel",
    "യഹ് സ്കിൽ": "Ezekiel",
    "എസക്കിയേൽ": "Ezekiel",
    "ദാനിയേൽ": "Daniel",
    "ഹോശേയാവ്": "Hosea",
    "ഹോശേയാ": "Hosea",
    "ഹോസിയ": "Hosea",
    "ഹോശേയ": "Hosea",
    "യോവേൽ": "Joel",
    "യോബേൽ": "Joel",
    "ആമോസ്": "Amos",
    "ഒബദ്യാവ്": "Obadiah",
    "ഒബദ്യാ": "Obadiah",
    "ഓബദ്യാവ്": "Obadiah",
    "യോന": "Jonah",
    "യോനാ": "Jonah",
    "മീഖാ പുസ്തകം": "Micah",
    "മീഖാപുസ്തകം": "Micah",
    "മീഖാ": "Micah",
    "നാഹും": "Nahum",
    "ഹബക്കൂക്ക്": "Habakkuk",
    "അബൂക്ക": "Habakkuk",
    "അബുക്ക": "Habakkuk",
    "സെഫന്യാവ്": "Zephaniah",
    "സെഫന്യാവു": "Zephaniah",
    "സഫ ന്യ": "Zephaniah",
    "സെഫന്യാ": "Zephaniah",
    "ഹഗ്ഗായി": "Haggai",
    "സെഖര്യാവ്": "Zechariah",
    "സക്കറിയയുടെ പുസ്തകം": "Zechariah",
    "സക്കറിയ": "Zechariah",
    "സെഖര്യാ": "Zechariah",
    "മലാഖി": "Malachi",
    # NT
    "മത്തായി": "Matthew",
    "മർക്കോസ്": "Mark",
    "ലൂക്കോസ്": "Luke",
    "യോഹന്നാൻ": "John",
    "അപ്പൊസ്തലപ്രവൃത്തികൾ": "Acts",
    "അപ്പോസ്തോല പ്രവർത്തി": "Acts",
    "റോമർ": "Romans",
    "1 കൊരിന്ത്യർ": "1 Corinthians",
    "1കൊരിന്ത്യർ": "1 Corinthians",
    "ഒന്ന് കൊരിന്ത്യർ": "1 Corinthians",
    "ഒന്ന് കൊരിന്ത്യര്": "1 Corinthians",
    "2 കൊരിന്ത്യർ": "2 Corinthians",
    "2കൊരിന്ത്യർ": "2 Corinthians",
    "രണ്ട് കൊരിന്ത്യർ": "2 Corinthians",
    "രണ്ട് കൊരിന്ത്യര്": "2 Corinthians",
    "2 കൊരിന്ത്യര്": "2 Corinthians",
    "ഗലാത്യർ": "Galatians",
    "ഗലാത്യ ലേഖനം": "Galatians",
    "എഫെസ്യർ": "Ephesians",
    "എഫെസ്യ ലേഖനം": "Ephesians",
    "ഫിലിപ്പിയർ": "Philippians",
    "കൊലോസ്യർ": "Colossians",
    "കൊലോസ്യർ ലേഖനം": "Colossians",
    "1 തെസ്സലോനിക്ക്യർ": "1 Thessalonians",
    "ഒന്നു തെസ്സലോനിക്ക": "1 Thessalonians",
    "1തെസ്സലോനിക്ക്യർ": "1 Thessalonians",
    "ഒന്ന് തെസ്സലോനിക്ക്യർ": "1 Thessalonians",
    "2 തെസ്സലോനിക്ക്യർ": "2 Thessalonians",
    "2തെസ്സലോനിക്ക്യർ": "2 Thessalonians",
    "രണ്ട് തെസ്സലോനിക്ക്യർ": "2 Thessalonians",
    "രണ്ട് സിലോണിൽ": "2 Thessalonians",
    "രണ്ട് തെസ്സലൊനീക്യർ": "2 Thessalonians",
    "2 തെസ്സലൊനീക്യർ": "2 Thessalonians",
    "1 തിമോത്തെയോസ്": "1 Timothy",
    "1തിമോത്തെയോസ്": "1 Timothy",
    "ഒന്ന് തീമോത്തിയോസ്": "1 Timothy",
    "1തിമോത്തി": "1 Timothy",
    "1 തിമോത്തി": "1 Timothy",
    "ഒന്ന് തിമോത്തി": "1 Timothy",
    "2 തിമോത്തിയോസ്": "2 Timothy",
    "2 തിമോത്തി": "2 Timothy",
    "രണ്ട് തി മതി": "2 Timothy",
    "2തിമോത്തെയോസ്": "2 Timothy",
    "രണ്ട് തിമോത്തെയോസ്": "2 Timothy",
    "തീത്തൊസ്": "Titus",
    "തീതൊസ്": "Titus",
    "തീത്തോസ്": "Titus",
    "ഫിറോസ്": "Titus",
    "ഫിലേമോൻ": "Philemon",
    "ഫിലേമോൻ ലേഖനം": "Philemon",
    "ഫിലോമിന ലേഖനം": "Philemon",
    "എബ്രായർ": "Hebrews",
    "എബ്രായ": "Hebrews",
    "എബ്രായർ എഴുതിയ ലേഖനം": "Hebrews",
    "യാക്കോബ്": "James",
    "യാക്കോബിനെ ലേഖനം": "James",
    "1 പത്രോസ്": "1 Peter",
    "1പത്രോസ്": "1 Peter",
    "പത്രോസിനെ ഒന്നാം ലേഖനം": "1 Peter",
    "ഒന്ന് പത്രോസ്": "1 Peter",
    "2 പത്രോസ്": "2 Peter",
    "2പത്രോസ്": "2 Peter",
    "രണ്ട് പത്രോസ്": "2 Peter",
    "രണ്ടു പത്രോസ്": "2 Peter",
    "പത്രോസിനെ രണ്ടാം ലേഖനം": "2 Peter",
    "1 യോഹന്നാൻ": "1 John",
    "1യോഹന്നാൻ": "1 John",
    "ഒന്ന് യോഹന്നാൻ": "1 John",
    "യോഹന്നാൻ എഴുതിയ ഒന്നാം ലേഖനം": "1 John",
    "2 യോഹന്നാൻ": "2 John",
    "2യോഹന്നാൻ": "2 John",
    "രണ്ട് യോഹന്നാൻ": "2 John",
    "യോഹന്നാൻ എഴുതിയ രണ്ടാം ലേഖനം": "2 John",
    "3 യോഹന്നാൻ": "3 John",
    "3യോഹന്നാൻ": "3 John",
    "മൂന്ന് യോഹന്നാൻ": "3 John",
    "യോഹന്നാൻ എഴുതിയ മൂന്നാം ലേഖനം": "3 John",
    "യൂദാസ്": "Jude",
    "യൂദാ": "Jude",
    "യൂദായുടെ ലേഖനം": "Jude",
    "വെളിപാടു": "Revelation",
    "വെളിപ്പാട്": "Revelation",
    "വെളിപാടുപുസ്തകം": "Revelation",
    "വെളിപാടു പുസ്തകം": "Revelation",
    "വെളിപാട്": "Revelation",
}

# ------------------- Malayalam digit map -------------------
ML_DIGITS = str.maketrans({
    "൦": "0", "൧": "1", "൨": "2", "൩": "3", "൪": "4",
    "൫": "5", "൬": "6", "൭": "7", "൮": "8", "൯": "9"
})

# ------------------- Ordinals + number words -------------------
ORDINAL_MAP = {
    # Ordinals
    "ഒന്നാം": "1", "ഒന്നാമത്തെ": "1",
    "രണ്ടാം": "2", "രണ്ടാമത്തെ": "2",
    "മൂന്നാം": "3", "മൂന്നാമത്തെ": "3",
    "നാലാം": "4", "നാലാമത്തെ": "4",
    "അഞ്ചാം": "5", "അഞ്ചാമത്തെ": "5",
    "ആറാം": "6", "ആറാമത്തെ": "6",
    "ഏഴാം": "7", "ഏഴാമത്തെ": "7",
    "എട്ടാം": "8", "എട്ടാമത്തെ": "8",
    "ഒൻപതാം": "9", "ഒൻപതാമത്തെ": "9",
    "പത്താം": "10", "പത്താമത്തെ": "10",
    "പതിനൊന്നാം": "11", "പതിനൊന്നാമത്തെ": "11",
    "പന്ത്രണ്ടാം": "12", "പന്ത്രണ്ടാമത്തെ": "12",
    "പതിമൂന്നാം": "13", "പതിമൂന്നാമത്തെ": "13",
    "പതിനാലാം": "14", "പതിനാലാമത്തെ": "14",
    "പതിനഞ്ചാം": "15", "പതിനഞ്ചാമത്തെ": "15",
    "പതിനാറാം": "16", "പതിനാറാമത്തെ": "16",
    "പതിനേഴാം": "17", "പതിനേഴാമത്തെ": "17", "പതിനേരാം": "17",
    "പതിനെട്ടാം": "18", "പതിനെട്ടാമത്തെ": "18",
    "പതിനൊൻപതാം": "19", "പതിനൊൻപതാമത്തെ": "19",
    "ഇരുപതാം": "20", "ഇരുപതാമത്തെ": "20",
    # Cardinal numbers
    "ഒന്ന്": "1", "ഒരൊന്ന്": "1", "ഒന്നു": "1", "ഒന്നാമൻ": "1",
    "രണ്ട്": "2", "രണ്ടു": "2", "രണ്ടാമൻ": "2",
    "മൂന്ന്": "3", "മൂന്നു": "3", "മുന്ന്": "3", "മൂന്നാമൻ": "3",
    "നാല്": "4", "നാലു": "4", "നാലാമൻ": "4",
    "അഞ്ച്": "5", "അഞ്ചു": "5", "അഞ്ചാമൻ": "5",
    "ആറ്": "6", "ആറു": "6", "ആറാമൻ": "6",
    "ഏഴ്": "7", "ഏഴു": "7", "ഏഴാമൻ": "7",
    "എട്ട്": "8", "എട്ടു": "8", "എട്ടാമൻ": "8",
    "ഒമ്പത്": "9", "ഒൻപതു": "9", "ഒമ്പതു": "9", "ഒമ്പതാമൻ": "9",
    "പത്ത്": "10", "പത്തു": "10", "പത്താമൻ": "10",
    "പതിനൊന്ന്": "11", "പതിനൊന്നു": "11",
    "പന്ത്രണ്ട്": "12", "പന്ത്രണ്ടു": "12",
    "പതിമൂന്ന്": "13", "പതിമൂന്നു": "13",
    "പതിനാല്": "14", "പതിനാലു": "14",
    "പതിനഞ്ച്": "15", "പതിനഞ്ചു": "15",
    "പതിനാറ്": "16", "പതിനാറു": "16",
    "പതിനേഴ്": "17", "പതിനേഴു": "17", "പതിനേഴാമൻ": "17",
    "പതിനെട്ട്": "18", "പതിനെട്ടു": "18",
    "പതിനൊൻപത്": "19", "പതിനൊമ്പത്": "19",
    "ഇരുപത്": "20", "ഇരുപതു": "20",
    "മുപ്പത്": "30", "മുപ്പതു": "30",
    "നാൽപ്പത്": "40", "നാൽപ്പതു": "40",
    "അൻപത്": "50", "അൻപതു": "50",
    "അറുപത്": "60", "അറുപതു": "60",
    "എഴുപത്": "70", "എഴുപതു": "70",
    "എൺപത്": "80", "എൺപതു": "80",
    "തൊണ്ണൂറ്": "90", "തൊണ്ണൂറു": "90",
    "നൂറ്": "100", "നൂറു": "100",
}

# ------------------- Fillers stripped in normalize_text -------------------
# ✅ Same concept as English/Hindi: strip chapter/verse keywords for main parser
NOISE_ML = [
    "അധ്യായം",    # chapter
    "അധ്യാ.",     # chapter abbrev
    "വാക്യം",     # verse
    "വാക്യങ്ങൾ",  # verses
    "വാ.",         # verse abbrev
    "പുസ്തകം",    # book
    "ലേഖനം",      # letter/epistle
    "എഴുതിയ",    # written (e.g. "written by")
    "പ്രകാരം",   # according to
    "തുറക്കൂ",   # open
    "വായിക്കൂ",  # read
    "നോക്കൂ",    # look/see
    "കാണുക",     # see
    "ഉള്ള",      # that is in
    "യുടെ",      # of (genitive suffix as full word)
]


# ------------------- Unicode / Chillu helpers -------------------
CHILLU_MAP = {
    "ൻ": "ന്",
    "ർ": "ര്",
    "ൾ": "ള്",
    "ൽ": "ല്",
    "ൺ": "ണ്",
    "ം": "മ്",
}


def normalize_chillu(s: str) -> str:
    for ch, rep in CHILLU_MAP.items():
        s = s.replace(ch, rep)
    return s


def strip_marks(s: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", s)
        if not unicodedata.combining(ch)
    )


def norm_for_match(s: str) -> str:
    """Normalize for fuzzy book name matching (strips diacritics, chillu)."""
    s = " ".join(s.split())
    s = normalize_chillu(s)
    s = strip_marks(s)
    return s


# ------------------- Core conversion -------------------

def normalize_digits(s: str) -> str:
    """Convert Malayalam digit characters to ASCII digits."""
    return s.translate(ML_DIGITS)


def convert_number_words(s: str) -> str:
    """
    ✅ Convert Malayalam ordinals and cardinal words to digits.
    Sorts by length descending so longer matches go first.
    """
    for k in sorted(ORDINAL_MAP.keys(), key=len, reverse=True):
        s = s.replace(k, ORDINAL_MAP[k])
    return s


# ------------------- Normalize functions -------------------

def normalize_text(s: str) -> str:
    """
    Full normalization for the main parser.
    ✅ Strips ALL filler/connector words (അധ്യായം, വാക്യം, etc.)
    ✅ Punctuation stripped FIRST so trailing chars don't block number conversion.
    Result: bare 'Book Chapter Verse' string for matching.
    """
    # Step 1: Malayalam digits → ASCII
    s = normalize_digits(s)
    # Step 2: ✅ Strip punctuation FIRST (same fix as English/Hindi)
    s = re.sub(r"[।\.,!?;:\-–]", " ", s)
    # Step 3: Convert number words & ordinals
    s = convert_number_words(s)
    # Step 4: Strip noise fillers
    for filler in NOISE_ML:
        s = s.replace(filler, " ")
    return " ".join(s.split())


def normalize_numbers_only(s: str) -> str:
    """
    ✅ Light normalization — converts digits and number words,
    strips punctuation, but KEEPS connector words like മുതൽ/വരെ/ഒപ്പം.
    Used for range detection and contextual cross-line detection.
    Mirrors the English normalize_numbers_only exactly.
    """
    # Step 1: Malayalam digits → ASCII
    s = normalize_digits(s)
    # Step 2: Strip punctuation
    s = re.sub(r"[।\.,!?;:\-–]", " ", s)
    # Step 3: Convert number words
    s = convert_number_words(s)
    return " ".join(s.split())


# ------------------- Book name resolver -------------------

def resolve_book(book_raw: str) -> str | None:
    """
    Find canonical English book name from Malayalam raw text.
    Uses chillu normalization + suffix trimming for fuzzy matching.
    """
    s = normalize_digits(" ".join(book_raw.split()))

    # Direct match first
    if s in BOOKS:
        return BOOKS[s]

    # Drop accidental trailing chapter digits
    parts = s.split()
    if parts and parts[-1].isdigit():
        s = " ".join(parts[:-1])

    # Handle numeric prefix (1, 2, 3)
    prefix_num = None
    parts = s.split()
    if parts and parts[0] in {"1", "2", "3"}:
        prefix_num = parts[0]
        s_wo_num = " ".join(parts[1:])
    else:
        s_wo_num = s

    # Trim Malayalam case suffixes
    CASE_SUFFIXES = ("ന്", "ിൽ", "ൽ", "ലെ", "ന്റെ", "യുടെ", "ത്തിൽ", "ക്കു", "ക്ക്")
    tokens = s_wo_num.split()
    if tokens:
        base_last = tokens[-1]
        for suf in CASE_SUFFIXES:
            if base_last.endswith(suf) and len(base_last) > len(suf) + 1:
                tokens[-1] = base_last[:-len(suf)]
                break
    s_wo_num_trim = " ".join(tokens)

    hay_variants = {
        norm_for_match(s_wo_num),
        norm_for_match(s_wo_num_trim),
    }

    best_key = None
    best_len = -1
    for k in BOOKS.keys():
        k_norm = norm_for_match(normalize_digits(k))
        for hay in hay_variants:
            if k_norm and k_norm in normalize_digits(hay):
                if len(k_norm) > best_len:
                    best_key = k
                    best_len = len(k_norm)

    if not best_key:
        if prefix_num and s_wo_num in BOOKS:
            eng = BOOKS[s_wo_num]
            if not eng.startswith((prefix_num + " ")):
                eng = f"{prefix_num} {eng}"
            return eng
        return None

    eng = BOOKS[best_key]
    if prefix_num:
        if eng.startswith(("1 ", "2 ", "3 ")):
            return eng
        return f"{prefix_num} {eng}"
    return eng


# ------------------- Regex pattern -------------------

# Matches: "Book chapter:verse" or "Book chapter verse"
# ✅ Allows dash ranges like "23:1-6"
REF_RE = re.compile(
    r"(?P<book>(?:[1-3]\s*)?[^\d:]+?)\s+(?P<chap>\d{1,3})\s*[: ]\s*(?P<verses>\d{1,3}(?:\s*[-–]\s*\d{1,3})?)"
)


# ------------------- Main parser -------------------

def parse_references(text: str):
    """
    Parse Malayalam Bible verse references from transcript text.
    ✅ Uses normalize_text (full strip) for clean matching.
    ✅ Also tries BOOKS-iteration fallback for chapter-only matches.
    Returns list of English references like ["John 3:16"].
    """
    if not text:
        return []

    results = []

    # ✅ Normalize first (strip fillers, convert digits/ordinals)
    t = normalize_text(text)

    # Pattern 1: REF_RE — catches "Book chapter:verse" and "Book chapter verse"
    for m in REF_RE.finditer(t):
        book_raw = m.group("book").strip()
        chap = m.group("chap")
        verses = m.group("verses").replace("–", "-")
        eng = resolve_book(book_raw)
        if eng:
            results.append(f"{eng} {chap}:{verses}")

    if results:
        return results

    # Pattern 2: BOOKS iteration — for chapter-only or missed refs
    # Try each known book name against the ORIGINAL text
    for ml_book in sorted(BOOKS.keys(), key=len, reverse=True):
        if ml_book not in text:
            continue

        eng_book = BOOKS[ml_book]
        idx = text.index(ml_book)
        after = text[idx + len(ml_book):]

        # Normalize the "after" section
        after = normalize_text(after)

        # Match chapter:verse
        m = re.search(r'(\d{1,3})\s*[:\-।]\s*(\d{1,3})', after)
        if m:
            results.append(f"{eng_book} {m.group(1)}:{m.group(2)}")
            continue

        # Match chapter then verse (separated)
        m2 = re.search(r'(\d{1,3})\D+(\d{1,3})', after)
        if m2:
            results.append(f"{eng_book} {m2.group(1)}:{m2.group(2)}")
            continue

        # ✅ Pattern 3: chapter only (context stored for cross-line detection)
        m3 = re.search(r'(\d{1,3})', after)
        if m3:
            results.append(f"{eng_book} {m3.group(1)}")

    return results


def parse_reference(text: str) -> str | None:
    """Parse the first verse reference in text."""
    refs = parse_references(text)
    return refs[0] if refs else None


# ------------------- Self-test -------------------

if __name__ == "__main__":
    tests = [
        "യോഹന്നാൻ 3:16",
        "യോഹന്നാൻ മൂന്നാം അധ്യായം പതിനാറാം വാക്യം",
        "സങ്കീർത്തനങ്ങൾ 23:1",
        "ഒന്നാം യോഹന്നാൻ 4:7",
        "1 പത്രോസ് 2:9",
        "സഭാപ്രസംഗി 3:1",
        "നെഹെമ്യാ 1:11",
        "2 കൊരിന്ത്യർ 5:17",
        "ദാനിയേൽ ആറ് പത്ത്",
        "എഫെസ്യർ ആറ് പത്ത് മുതൽ പന്ത്രണ്ട് വരെ",
    ]

    print("=" * 70)
    print("MALAYALAM PARSER TEST")
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
