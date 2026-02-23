# -*- coding: utf-8 -*-

import re

# ------------------- Hindi → English book mapping -------------------

BOOKS = {

    # OT
    "उत्पत्ति": "Genesis",
    "निर्गमन": "Exodus",
    "लैव्यव्यवस्था": "Leviticus",
    "लैव्य": "Leviticus",
    "गिनती": "Numbers",
    "व्यवस्थाविवरण": "Deuteronomy",
    "व्यवस्था": "Deuteronomy",
    "यहोशू": "Joshua",
    "न्यायियों": "Judges",
    "न्यायाधीश": "Judges",
    "रूत": "Ruth",

    # Numbered OT
    "1 शमूएल": "1 Samuel",
    "1शमूएल": "1 Samuel",
    "एक शमूएल": "1 Samuel",
    "2 शमूएल": "2 Samuel",
    "2शमूएल": "2 Samuel",
    "दो शमूएल": "2 Samuel",

    "1 राजाओं": "1 Kings",
    "1राजाओं": "1 Kings",
    "एक राजाओं": "1 Kings",
    "2 राजाओं": "2 Kings",
    "2राजाओं": "2 Kings",
    "दो राजाओं": "2 Kings",

    "1 इतिहास": "1 Chronicles",
    "1इतिहास": "1 Chronicles",
    "एक इतिहास": "1 Chronicles",
    "2 इतिहास": "2 Chronicles",
    "2इतिहास": "2 Chronicles",
    "दो इतिहास": "2 Chronicles",

    # More OT
    "एज्रा": "Ezra",
    "नहेम्याह": "Nehemiah",
    "एस्तेर": "Esther",
    "अय्यूब": "Job",
    "भजन संहिता": "Psalms",
    "भजन": "Psalms",
    "नीतिवचन": "Proverbs",
    "सभोपदेशक": "Ecclesiastes",
    "श्रेष्ठगीत": "Song of Solomon",
    "यशायाह": "Isaiah",
    "यशाया": "Isaiah",
    "यिर्मयाह": "Jeremiah",
    "यिर्मया": "Jeremiah",
    "विलापगीत": "Lamentations",
    "यहेजकेल": "Ezekiel",
    "दानिय्येल": "Daniel",
    "दानिएल": "Daniel",
    "होशे": "Hosea",
    "योएल": "Joel",
    "आमोस": "Amos",
    "ओबद्याह": "Obadiah",
    "योना": "Jonah",
    "मीका": "Micah",
    "नहूम": "Nahum",
    "हबक्कूक": "Habakkuk",
    "सपन्याह": "Zephaniah",
    "हाग्गै": "Haggai",
    "जकर्याह": "Zechariah",
    "मलाकी": "Malachi",

    # NT
    "मत्ती": "Matthew",
    "मरकुस": "Mark",
    "लूका": "Luke",
    "यूहन्ना": "John",
    "प्रेरितों के काम": "Acts",
    "प्रेरितों": "Acts",
    "रोमियों": "Romans",

    "1 कुरिन्थियों": "1 Corinthians",
    "1कुरिन्थियों": "1 Corinthians",
    "एक कुरिन्थियों": "1 Corinthians",
    "2 कुरिन्थियों": "2 Corinthians",
    "2कुरिन्थियों": "2 Corinthians",
    "दो कुरिन्थियों": "2 Corinthians",

    "गलातियों": "Galatians",
    "इफिसियों": "Ephesians",
    "फिलिप्पियों": "Philippians",
    "कुलुस्सियों": "Colossians",

    "1 थिस्सलुनीकियों": "1 Thessalonians",
    "1थिस्सलुनीकियों": "1 Thessalonians",
    "एक थिस्सलुनीकियों": "1 Thessalonians",
    "2 थिस्सलुनीकियों": "2 Thessalonians",
    "2थिस्सलुनीकियों": "2 Thessalonians",
    "दो थिस्सलुनीकियों": "2 Thessalonians",

    "1 तीमुथियुस": "1 Timothy",
    "1तीमुथियुस": "1 Timothy",
    "एक तीमुथियुस": "1 Timothy",
    "2 तीमुथियुस": "2 Timothy",
    "2तीमुथियुस": "2 Timothy",
    "दो तीमुथियुस": "2 Timothy",

    "तीतुस": "Titus",
    "फिलेमोन": "Philemon",
    "इब्रानियों": "Hebrews",
    "याकूब": "James",

    "1 पतरस": "1 Peter",
    "1पतरस": "1 Peter",
    "एक पतरस": "1 Peter",
    "2 पतरस": "2 Peter",
    "2पतरस": "2 Peter",
    "दो पतरस": "2 Peter",

    "1 यूहन्ना": "1 John",
    "1यूहन्ना": "1 John",
    "एक यूहन्ना": "1 John",
    "2 यूहन्ना": "2 John",
    "2यूहन्ना": "2 John",
    "दो यूहन्ना": "2 John",
    "3 यूहन्ना": "3 John",
    "3यूहन्ना": "3 John",
    "तीन यूहन्ना": "3 John",

    "यहूदा": "Jude",
    "प्रकाशितवाक्य": "Revelation",
    "प्रकाशन": "Revelation",
}

# ------------------- Hindi digit map -------------------

HI_DIGITS = str.maketrans({
    "०": "0", "१": "1", "२": "2", "३": "3", "४": "4",
    "५": "5", "६": "6", "७": "7", "८": "8", "९": "9"
})

# ------------------- Hindi number words -------------------

NUMBER_MAP = {
    "एक": "1",
    "दो": "2",
    "तीन": "3",
    "चार": "4",
    "पाँच": "5",
    "पांच": "5",
    "छः": "6",
    "छह": "6",
    "सात": "7",
    "आठ": "8",
    "नौ": "9",
    "दस": "10",
    "ग्यारह": "11",
    "बारह": "12",
    "तेरह": "13",
    "चौदह": "14",
    "पन्द्रह": "15",
    "सोलह": "16",
    "सत्रह": "17",
    "अठारह": "18",
    "उन्नीस": "19",
    "बीस": "20",
    "इक्कीस": "21",
    "बाईस": "22",
    "तेईस": "23",
    "चौबीस": "24",
    "पच्चीस": "25",
    "छब्बीस": "26",
    "सत्ताईस": "27",
    "अट्ठाईस": "28",
    "उनतीस": "29",
    "तीस": "30",
}

# ------------------- Fillers to strip -------------------

BOOK_FILLERS = ["अध्याय", "वचन", "पद"]

# ------------------- Normalizers -------------------

def normalize_digits(s: str) -> str:
    return s.translate(HI_DIGITS)

def normalize_number_words(s: str) -> str:
    for k in sorted(NUMBER_MAP.keys(), key=len, reverse=True):
        s = s.replace(k, NUMBER_MAP[k])
    return s

def clean_book_name(book: str) -> str:
    for junk in BOOK_FILLERS:
        book = book.replace(junk, "").strip()
    return " ".join(book.split())

# ------------------- Main parser -------------------

def parse_references(text: str):
    """
    Parse Hindi Bible verse references from transcript text.
    Returns list of English references like ["John 3:16"]
    """
    if not text:
        return []

    results = []

    # Normalize Hindi digits and number words
    text = normalize_digits(text)
    text = normalize_number_words(text)

    # Try matching known book names
    for hi_book in sorted(BOOKS.keys(), key=len, reverse=True):
        if hi_book in text:
            eng_book = BOOKS[hi_book]
            idx = text.index(hi_book)
            after = text[idx + len(hi_book):].strip()

            # Strip fillers
            for filler in BOOK_FILLERS:
                after = after.replace(filler, "").strip()

            # Match chapter:verse pattern
            m = re.search(r'(\d{1,3})\s*[:\-।]\s*(\d{1,3})', after)
            if m:
                chapter = m.group(1)
                verse = m.group(2)
                results.append(f"{eng_book} {chapter}:{verse}")
                continue

            # Match chapter then verse separately
            m2 = re.search(r'(\d{1,3})\D+(\d{1,3})', after)
            if m2:
                chapter = m2.group(1)
                verse = m2.group(2)
                results.append(f"{eng_book} {chapter}:{verse}")

    return results
