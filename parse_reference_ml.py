# -*- coding: utf-8 -*-
import re
import unicodedata

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

ORDINAL_WORDS_ENG = {"first": "1", "second": "2", "third": "3"}

NUMBER_MAP_ENG = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}

NOISE_ENG = (r"\b(let s|let us|read|the|a|an|chapter|chap|ch"
             r"|verse|verses|versus|vs|forward|attention|to|now|our"
             r"|turn|open|look|see|go|pay|pages|bible|book|books"
             r"|words|word|says|said|saying|it|in|and|at|from"
             r"|today|we|will|are|is|was)\b")

REF_RE_ENG = re.compile(
    r"(?P<book>(?:[123] )?[a-z]+(?:[a-z ]+)?)"
    r"\s+"
    r"(?P<chap>\d{1,3})"
    r"(?:[:\s]+"
    r"(?P<verses>\d{1,3}))?",
    re.IGNORECASE
)

# ------------------- Malayalam → English book mapping -------------------
BOOKS_ML = {
    "ഉല്പത്തി": "Genesis", "പുറപ്പാട്": "Exodus", "ലേവ്യപുസ്തകം": "Leviticus", "ലേവ്യ": "Leviticus",
    "ലേവ്യപു": "Leviticus", "സംഖ്യാപുസ്തകം": "Numbers", "സംഖ്യ": "Numbers", "ആവർത്തനം": "Deuteronomy",
    "യോശുവ": "Joshua", "ന്യായാധിപന്മാർ": "Judges", "റൂത്ത്": "Ruth", "രൂത്ത്": "Ruth",
    "1 ശമുവേൽ": "1 Samuel", "1ശമൂവേൽ": "1 Samuel", "ഒന്ന് ശമൂവേൽ": "1 Samuel",
    "2 ശമൂവേൽ": "2 Samuel", "2ശമൂവേൽ": "2 Samuel", "രണ്ട് ശമൂവേൽ": "2 Samuel",
    "1 രാജാ": "1 Kings", "ഒന്നു രാജ്": "1 Kings", "ഒന്ന് രാജാ": "1 Kings",
    "1 രാജാക്കന്മാർ": "1 Kings", "1രാജാക്കന്മാർ": "1 Kings", "ഒന്ന് രാജാക്കന്മാർ": "1 Kings",
    "2 രാജാ": "2 Kings", "രണ്ടു രാജ്": "2 Kings", "രണ്ട് രാജാ": "2 Kings",
    "2 രാജാക്കന്മാർ": "2 Kings", "2രാജാക്കന്മാർ": "2 Kings", "രണ്ട് രാജാക്കന്മാർ": "2 Kings",
    "1 ദിനവൃത്താന്തം": "1 Chronicles", "1ദിനവൃത്താന്തം": "1 Chronicles", "ഒന്ന് ദിനവൃത്താന്തം": "1 Chronicles",
    "2 ദിനവൃത്താന്തം": "2 Chronicles", "2ദിനവൃത്താന്തം": "2 Chronicles", "രണ്ട് ദിനവൃത്താന്തം": "2 Chronicles",
    "1 ദിനവൃത്താന്തങ്ങൾ": "1 Chronicles", "1ദിനവൃത്താന്തങ്ങൾ": "1 Chronicles", "ഒന്ന് ദിനവൃത്താന്തങ്ങൾ": "1 Chronicles",
    "2 ദിനവൃത്താന്തങ്ങൾ": "2 Chronicles", "2ദിനവൃത്താന്തങ്ങൾ": "2 Chronicles", "രണ്ട് ദിനവൃത്താന്തങ്ങൾ": "2 Chronicles",
    "എസ്രാ": "Ezra", "എസ്ര": "Ezra", "നെഹെമ്യാവു": "Nehemiah", "നെഹെമ്യാ": "Nehemiah", "നെഹമിയ": "Nehemiah",
    "എസ്തേർ": "Esther", "എസ്ഥേർ": "Esther", "ഇയ്യോബ്": "Job", "സങ്കീർത്തനങ്ങൾ": "Psalms", "സങ്കീർത്തനം": "Psalms",
    "സദൃശ്യവാക്യങ്ങൾ": "Proverbs", "സദൃശ്യവാക്യം": "Proverbs", "സദൃശ്യം": "Proverbs", "സഭാപ്രസംഗി": "Ecclesiastes",
    "പ്രസംഗി": "Ecclesiastes", "ഉത്തമഗീതം": "Song of Solomon", "പരമഗീതം": "Song of Solomon", "യെശയ്യാവ്": "Isaiah",
    "യെശയ്യാ": "Isaiah", "ഏഷ്യാ": "Isaiah", "യിരെമ്യാവ്": "Jeremiah", "ഇര മ്യാവൂ": "Jeremiah", "യിരെമ്യാ": "Jeremiah",
    "വിലാപങ്ങൾ": "Lamentations", "വിലാപം": "Lamentations", "യെഹെസ്കേൽ": "Ezekiel", "യഹ് സ്കിൽ": "Ezekiel",
    "എസക്കിയേൽ": "Ezekiel", "ദാനിയേൽ": "Daniel", "ഹോശേയാവ്": "Hosea", "ഹോശേയാ": "Hosea", "ഹോസിയ": "Hosea",
    "ഹോശേയ": "Hosea", "യോവേൽ": "Joel", "യോബേൽ": "Joel", "ആമോസ്": "Amos", "ഒബദ്യാവ്": "Obadiah", "ഒബദ്യാ": "Obadiah",
    "ഓബദ്യാവ്": "Obadiah", "യോന": "Jonah", "യോനാ": "Jonah", "മീഖാ പുസ്തകം": "Micah", "മീഖാപുസ്തകം": "Micah",
    "മീഖാ": "Micah", "നാഹും": "Nahum", "ഹബക്കൂക്ക്": "Habakkuk", "അബൂക്ക": "Habakkuk", "അബുക്ക": "Habakkuk",
    "സെഫന്യാവ്": "Zephaniah", "സെഫന്യാവു": "Zephaniah", "സഫ ന്യ": "Zephaniah", "സെഫന്യാ": "Zephaniah",
    "ഹഗ്ഗായി": "Haggai", "സെഖര്യാവ്": "Zechariah", "സക്കറിയയുടെ പുസ്തകം": "Zechariah", "സക്കറിയ": "Zechariah",
    "സെഖര്യാ": "Zechariah", "മലാഖി": "Malachi",
    "മത്തായി": "Matthew", "മർക്കോസ്": "Mark", "ലൂക്കോസ്": "Luke", "യോഹന്നാൻ": "John",
    "അപ്പൊസ്തലപ്രവൃത്തികൾ": "Acts", "അപ്പോസ്തോല പ്രവർത്തി": "Acts", "റോമർ": "Romans",
    "1 കൊരിന്ത്യർ": "1 Corinthians", "1കൊരിന്ത്യർ": "1 Corinthians", "ഒന്ന് കൊരിന്ത്യർ": "1 Corinthians",
    "ഒന്ന് കൊരിന്ത്യര്": "1 Corinthians", "2 കൊരിന്ത്യർ": "2 Corinthians", "2കൊരിന്ത്യർ": "2 Corinthians",
    "രണ്ട് കൊരിന്ത്യർ": "2 Corinthians", "രണ്ട് കൊരിന്ത്യര്": "2 Corinthians", "2 കൊരിന്ത്യര്": "2 Corinthians",
    "ഗലാത്യർ": "Galatians", "ഗലാത്യ ലേഖനം": "Galatians", "എഫെസ്യർ": "Ephesians", "എഫെസ്യ ലേഖനം": "Ephesians",
    "ഫിലിപ്പിയർ": "Philippians", "കൊലോസ്യർ": "Colossians", "കൊലോസ്യർ ലേഖനം": "Colossians",
    "1 തെസ്സലോനിക്ക്യർ": "1 Thessalonians", "ഒന്നു തെസ്സലോനിക്ക": "1 Thessalonians", "1തെസ്സലോനിക്ക്യർ": "1 Thessalonians",
    "ഒന്ന് തെസ്സലോനിക്ക്യർ": "1 Thessalonians", "2 തെസ്സലോനിക്ക്യർ": "2 Thessalonians", "2തെസ്സലോനിക്ക്യർ": "2 Thessalonians",
    "രണ്ട് തെസ്സലോനിക്ക്യർ": "2 Thessalonians", "രണ്ട് സിലോണിൽ": "2 Thessalonians", "രണ്ട് തെസ്സലൊനീക്യർ": "2 Thessalonians",
    "2 തെസ്സലൊനീക്യർ": "2 Thessalonians", "1 തിമോത്തെയോസ്": "1 Timothy", "1തിമോത്തെയോസ്": "1 Timothy",
    "ഒന്ന് തീമോത്തിയോസ്": "1 Timothy", "1തിമോത്തി": "1 Timothy", "1 തിമോത്തി": "1 Timothy", "ഒന്ന് തിമോത്തി": "1 Timothy",
    "2 തിമോത്തിയോസ്": "2 Timothy", "2 തിമോത്തി": "2 Timothy", "രണ്ട് തി മതി": "2 Timothy", "2തിമോത്തെയോസ്": "2 Timothy",
    "രണ്ട് തിമോത്തെയോസ്": "2 Timothy", "തീത്തൊസ്": "Titus", "തീതൊസ്": "Titus", "തീത്തോസ്": "Titus", "ഫിറോസ്": "Titus",
    "ഫിലേമോൻ": "Philemon", "ഫിലേമോൻ ലേഖനം": "Philemon", "ഫിലോമിന ലേഖനം": "Philemon", "എബ്രായർ": "Hebrews",
    "എബ്രായ": "Hebrews", "എബ്രായർ എഴുതിയ ലേഖനം": "Hebrews", "യാക്കോബ്": "James", "യാക്കോബിനെ ലേഖനം": "James",
    "1 പത്രോസ്": "1 Peter", "1പത്രോസ്": "1 Peter", "പത്രോസിനെ ഒന്നാം ലേഖനം": "1 Peter", "ഒന്ന് പത്രോസ്": "1 Peter",
    "2 പത്രോസ്": "2 Peter", "2പത്രോസ്": "2 Peter", "രണ്ട് പത്രോസ്": "2 Peter", "രണ്ടു പത്രോസ്": "2 Peter",
    "പത്രോസിനെ രണ്ടാം ലേഖനം": "2 Peter", "1 യോഹന്നാൻ": "1 John", "1യോഹന്നാൻ": "1 John", "ഒന്ന് യോഹന്നാൻ": "1 John",
    "യോഹന്നാൻ എഴുതിയ ഒന്നാം ലേഖനം": "1 John", "2 യോഹന്നാൻ": "2 John", "2യോഹന്നാൻ": "2 John",
    "രണ്ട് യോഹന്നാൻ": "2 John", "യോഹന്നാൻ എഴുതിയ രണ്ടാം ലേഖനം": "2 John", "3 യോഹന്നാൻ": "3 John",
    "3യോഹന്നാൻ": "3 John", "മൂന്ന് യോഹന്നാൻ": "3 John", "യോഹന്നാൻ എഴുതിയ മൂന്നാം ലേഖനം": "3 John",
    "യൂദാസ്": "Jude", "യൂദാ": "Jude", "യൂദായുടെ ലേഖനം": "Jude", "വെളിപാടു": "Revelation", "വെളിപ്പാട്": "Revelation",
    "വെളിപാടുപുസ്തകം": "Revelation", "വെളിപാടു പുസ്തകം": "Revelation", "വെളിപാട്": "Revelation",
}

ML_DIGITS = str.maketrans({
    "൦": "0", "൧": "1", "൨": "2", "൩": "3", "൪": "4",
    "൫": "5", "൬": "6", "൭": "7", "൮": "8", "൯": "9"
})

ORDINAL_MAP_ML = {
    "ഒന്നാം": "1", "ഒന്നാമത്തെ": "1", "രണ്ടാം": "2", "രണ്ടാമത്തെ": "2",
    "മൂന്നാം": "3", "മൂന്നാമത്തെ": "3", "നാലാം": "4", "നാലാമത്തെ": "4",
    "അഞ്ചാം": "5", "അഞ്ചാമത്തെ": "5", "ആറാം": "6", "ആറാമത്തെ": "6",
    "ഏഴാം": "7", "ഏഴാമത്തെ": "7", "എട്ടാം": "8", "എട്ടാമത്തെ": "8",
    "ഒൻപതാം": "9", "ഒൻപതാമത്തെ": "9", "പത്താം": "10", "പത്താമത്തെ": "10",
    "പതിനൊന്നാം": "11", "പതിനൊന്നാമത്തെ": "11", "പന്ത്രണ്ടാം": "12", "പന്ത്രണ്ടാമത്തെ": "12",
    "പതിമൂന്നാം": "13", "പതിമൂന്നാമത്തെ": "13", "പതിനാലാം": "14", "പതിനാലാമത്തെ": "14",
    "പതിനഞ്ചാം": "15", "പതിനഞ്ചാമത്തെ": "15", "പതിനാറാം": "16", "പതിനാറാമത്തെ": "16",
    "പതിനേഴാം": "17", "പതിനേഴാമത്തെ": "17", "പതിനേരാം": "17", "പതിനെട്ടാം": "18", "പതിനെട്ടാമത്തെ": "18",
    "പതിനൊൻപതാം": "19", "പതിനൊൻപതാമത്തെ": "19", "ഇരുപതാം": "20", "ഇരുപതാമത്തെ": "20",
    "ഇരുപത്തി": "20 ", "മുപ്പത്തി": "30 ", "നാൽപ്പത്തി": "40 ", "അൻപത്തി": "50 ",
    "അറുപത്തി": "60 ", "എഴുപത്തി": "70 ", "എൺപത്തി": "80 ", "തൊണ്ണൂറ്റി": "90 ",
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
    "പതിനൊന്ന്": "11", "പതിനൊന്നു": "11", "പന്ത്രണ്ട്": "12", "പന്ത്രണ്ടു": "12",
    "പതിമൂന്ന്": "13", "പതിമൂന്നു": "13", "പതിനാല്": "14", "പതിനാലു": "14",
    "പതിനഞ്ച്": "15", "പതിനഞ്ചു": "15", "പതിനാറ്": "16", "പതിനാറു": "16",
    "പതിനേഴ്": "17", "പതിനേഴു": "17", "പതിനേഴാമൻ": "17",
    "പതിനെട്ട്": "18", "പതിനെട്ടു": "18", "പതിനൊൻപത്": "19", "പതിനൊമ്പത്": "19",
    "ഇരുപത്": "20", "ഇരുപതു": "20", "മുപ്പത്": "30", "മുപ്പതു": "30",
    "നാൽപ്പത്": "40", "നാൽപ്പതു": "40", "അൻപത്": "50", "അൻപതു": "50",
    "അറുപത്": "60", "അറുപതു": "60", "എഴുപത്": "70", "എഴുപതു": "70",
    "എൺപത്": "80", "എൺപതു": "80", "തൊണ്ണൂറ്": "90", "തൊണ്ണൂറു": "90",
    "നൂറ്": "100", "നൂറു": "100",
}

NOISE_ML = [
    "അധ്യായം", "അധ്യാ.", "വാക്യം", "വാക്യങ്ങൾ", "വാ.", "പുസ്തകം", 
    "ലേഖനം", "എഴുതിയ", "പ്രകാരം", "തുറക്കൂ", "വായിക്കൂ", "നോക്കൂ", 
    "കാണുക", "ഉള്ള", "യുടെ"
]

CHILLU_MAP = {"ൻ": "ന്", "ർ": "ര്", "ൾ": "ള്", "ൽ": "ല്", "ൺ": "ണ്", "ം": "മ്"}

# ------------------- English Math & Resolver (From parse_eng) -------------------
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

# ------------------- Malayalam Normalizers -------------------
def normalize_chillu(s: str) -> str:
    for ch, rep in CHILLU_MAP.items():
        s = s.replace(ch, rep)
    return s

def strip_marks(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if not unicodedata.combining(ch))

def norm_for_match(s: str) -> str:
    s = " ".join(s.split())
    s = normalize_chillu(s)
    return strip_marks(s)

def normalize_digits_ml(s: str) -> str:
    return s.translate(ML_DIGITS)

def convert_number_words_ml(s: str) -> str:
    for k in sorted(ORDINAL_MAP_ML.keys(), key=len, reverse=True):
        s = s.replace(k, ORDINAL_MAP_ML[k])
    s = re.sub(
        r'\b(20|30|40|50|60|70|80|90)\s+([1-9])\b', 
        lambda m: str(int(m.group(1)) + int(m.group(2))), 
        s
    )
    return s

def normalize_numbers_only(s: str) -> str:
    """
    Combined Normalizer: Processes English numbers FIRST, then Malayalam numbers.
    """
    s = s.lower()
    for word, num in ORDINAL_WORDS_ENG.items():
        s = re.sub(rf"\b{word}\b", num, s)
        
    s = convert_word_numbers_eng(s)
    s = normalize_digits_ml(s)
    s = re.sub(r"[।\.,!?;:\-–]", " ", s)
    s = convert_number_words_ml(s)
    return " ".join(s.split())

def resolve_book_ml(book_raw: str) -> str | None:
    s = normalize_digits_ml(" ".join(book_raw.split()))
    if s in BOOKS_ML:
        return BOOKS_ML[s]

    parts = s.split()
    if parts and parts[-1].isdigit():
        s = " ".join(parts[:-1])

    prefix_num = None
    parts = s.split()
    if parts and parts[0] in {"1", "2", "3"}:
        prefix_num = parts[0]
        s_wo_num = " ".join(parts[1:])
    else:
        s_wo_num = s

    CASE_SUFFIXES = ("ന്", "ിൽ", "ൽ", "ലെ", "ന്റെ", "യുടെ", "ത്തിൽ", "ക്കു", "ക്ക്")
    tokens = s_wo_num.split()
    if tokens:
        base_last = tokens[-1]
        for suf in CASE_SUFFIXES:
            if base_last.endswith(suf) and len(base_last) > len(suf) + 1:
                tokens[-1] = base_last[:-len(suf)]
                break
    s_wo_num_trim = " ".join(tokens)

    hay_variants = {norm_for_match(s_wo_num), norm_for_match(s_wo_num_trim)}
    best_key, best_len = None, -1

    for k in BOOKS_ML.keys():
        k_norm = norm_for_match(normalize_digits_ml(k))
        for hay in hay_variants:
            if k_norm and k_norm in normalize_digits_ml(hay):
                if len(k_norm) > best_len:
                    best_key = k
                    best_len = len(k_norm)

    if not best_key:
        if prefix_num and s_wo_num in BOOKS_ML:
            eng = BOOKS_ML[s_wo_num]
            if not eng.startswith((prefix_num + " ")):
                eng = f"{prefix_num} {eng}"
            return eng
        return None

    eng = BOOKS_ML[best_key]
    if prefix_num:
        if eng.startswith(("1 ", "2 ", "3 ")):
            return eng
        return f"{prefix_num} {eng}"
    return eng

# ------------------- Main Code-Switched Parser -------------------
REF_RE_ML = re.compile(
    r"(?P<book>(?:[1-3]\s*)?[^\d:]+?)\s+(?P<chap>\d{1,3})\s*[: ]\s*(?P<verses>\d{1,3}(?:\s*[-–]\s*\d{1,3})?)"
)

def parse_references(text: str):
    if not text:
        return []

    results = []
    
    # Pre-process text to convert English & ML number words to digits
    t = text.lower()
    for word, num in ORDINAL_WORDS_ENG.items():
        t = re.sub(rf"\b{word}\b", num, t)
    t = convert_word_numbers_eng(t)
    t = normalize_digits_ml(t)
    t = convert_number_words_ml(t)

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

    # 2. Malayalam Parser Pipeline (Regex)
    t_ml = t
    for filler in NOISE_ML:
        t_ml = t_ml.replace(filler, " ")
    t_ml = re.sub(NOISE_ENG, " ", t_ml)
    t_ml = " ".join(t_ml.split())

    for m in REF_RE_ML.finditer(t_ml):
        book_raw = m.group("book").strip()
        chap = m.group("chap")
        verses = m.group("verses").replace("–", "-")
        eng = resolve_book_ml(book_raw)
        if eng:
            results.append(f"{eng} {chap}:{verses}")

    if results:
        return results

    # 3. Malayalam Parser Pipeline (Brute Force context)
    for ml_book in sorted(BOOKS_ML.keys(), key=len, reverse=True):
        if ml_book in t:
            eng_book = BOOKS_ML[ml_book]
            idx = t.index(ml_book)
            after = t[idx + len(ml_book):]
            
            for filler in NOISE_ML:
                after = after.replace(filler, " ")
            after = re.sub(NOISE_ENG, " ", after)
            after = " ".join(after.split())

            m = re.search(r'(\d{1,3})\s*[:\-।]\s*(\d{1,3})', after)
            if m:
                results.append(f"{eng_book} {m.group(1)}:{m.group(2)}")
                continue

            m2 = re.search(r'(\d{1,3})\D+(\d{1,3})', after)
            if m2:
                results.append(f"{eng_book} {m2.group(1)}:{m2.group(2)}")
                continue

            m3 = re.search(r'(\d{1,3})', after)
            if m3:
                results.append(f"{eng_book} {m3.group(1)}")
                continue

    return results

def parse_reference(text: str) -> str | None:
    refs = parse_references(text)
    return refs[0] if refs else None