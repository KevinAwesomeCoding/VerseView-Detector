# -*- coding: utf-8 -*-
import requests
import certifi
import logging
import re

logger = logging.getLogger(__name__)

TIMEOUT = 6

# ── Book name → number map (for biblebytopic) ──
BOOK_NUMBERS = {
    "genesis": 1, "exodus": 2, "leviticus": 3, "numbers": 4,
    "deuteronomy": 5, "joshua": 6, "judges": 7, "ruth": 8,
    "1 samuel": 9, "2 samuel": 10, "1 kings": 11, "2 kings": 12,
    "1 chronicles": 13, "2 chronicles": 14, "ezra": 15, "nehemiah": 16,
    "esther": 17, "job": 18, "psalms": 19, "psalm": 19, "proverbs": 20,
    "ecclesiastes": 21, "song of solomon": 22, "isaiah": 23, "jeremiah": 24,
    "lamentations": 25, "ezekiel": 26, "daniel": 27, "hosea": 28,
    "joel": 29, "amos": 30, "obadiah": 31, "jonah": 32, "micah": 33,
    "nahum": 34, "habakkuk": 35, "zephaniah": 36, "haggai": 37,
    "zechariah": 38, "malachi": 39, "matthew": 40, "mark": 41,
    "luke": 42, "john": 43, "acts": 44, "romans": 45,
    "1 corinthians": 46, "2 corinthians": 47, "galatians": 48,
    "ephesians": 49, "philippians": 50, "colossians": 51,
    "1 thessalonians": 52, "2 thessalonians": 53, "1 timothy": 54,
    "2 timothy": 55, "titus": 56, "philemon": 57, "hebrews": 58,
    "james": 59, "1 peter": 60, "2 peter": 61, "1 john": 62,
    "2 john": 63, "3 john": 64, "jude": 65, "revelation": 66,
}

# ── bible.helloao.org book IDs ──
HELLOAO_BOOK_IDS = {
    "genesis": "GEN", "exodus": "EXO", "leviticus": "LEV", "numbers": "NUM",
    "deuteronomy": "DEU", "joshua": "JOS", "judges": "JDG", "ruth": "RUT",
    "1 samuel": "1SA", "2 samuel": "2SA", "1 kings": "1KI", "2 kings": "2KI",
    "1 chronicles": "1CH", "2 chronicles": "2CH", "ezra": "EZR", "nehemiah": "NEH",
    "esther": "EST", "job": "JOB", "psalms": "PSA", "psalm": "PSA",
    "proverbs": "PRO", "ecclesiastes": "ECC", "song of solomon": "SNG",
    "isaiah": "ISA", "jeremiah": "JER", "lamentations": "LAM", "ezekiel": "EZK",
    "daniel": "DAN", "hosea": "HOS", "joel": "JOL", "amos": "AMO",
    "obadiah": "OBA", "jonah": "JON", "micah": "MIC", "nahum": "NAM",
    "habakkuk": "HAB", "zephaniah": "ZEP", "haggai": "HAG", "zechariah": "ZEC",
    "malachi": "MAL", "matthew": "MAT", "mark": "MRK", "luke": "LUK",
    "john": "JHN", "acts": "ACT", "romans": "ROM", "1 corinthians": "1CO",
    "2 corinthians": "2CO", "galatians": "GAL", "ephesians": "EPH",
    "philippians": "PHP", "colossians": "COL", "1 thessalonians": "1TH",
    "2 thessalonians": "2TH", "1 timothy": "1TI", "2 timothy": "2TI",
    "titus": "TIT", "philemon": "PHM", "hebrews": "HEB", "james": "JAS",
    "1 peter": "1PE", "2 peter": "2PE", "1 john": "1JN", "2 john": "2JN",
    "3 john": "3JN", "jude": "JUD", "revelation": "REV",
}

# ── Translation routing ──
# Maps user-selected translation → which APIs support it
TRANSLATION_APIS = {
    "kjv":  ["bible_api_com", "biblebytopic", "helloao"],
    "web":  ["bible_api_com", "biblebytopic", "helloao"],
    "asv":  ["biblebytopic", "helloao"],
    "net":  ["biblebytopic", "biblesdk", "helloao"],
    "oeb":  ["bible_api_com"],
    "webbe":["bible_api_com"],
    "nlt":  ["helloao"],
    "esv":  ["helloao"],
    "niv":  ["helloao"],
    "nasb": ["helloao"],
    "amp":  ["helloao"],
    "nkjv": ["helloao"],
    "csb":  ["helloao"],
    "msg":  ["helloao"],
}


def _parse_ref(ref: str):
    """Parse 'John 3:16' → (book, chapter, verse)"""
    ref = ref.strip()
    m = re.match(r'^(.+?)\s+(\d+):(\d+)$', ref)
    if not m:
        return None, None, None
    return m.group(1).lower(), m.group(2), m.group(3)


# ─────────────────────────────────────
# API 1: bible-api.com (Tim Morgan)
# Supports: kjv, web, oeb, webbe, clementine
# ─────────────────────────────────────
def _fetch_bible_api_com(ref: str, translation: str) -> str | None:
    try:
        url = f"https://bible-api.com/{ref.replace(' ', '+')}?translation={translation}"
        r   = requests.get(url, timeout=TIMEOUT, verify=certifi.where())
        if r.status_code == 200:
            text = r.json().get("text", "").strip()
            if text:
                logger.debug(f"✅ bible-api.com: {ref} [{translation}]")
                return text
    except Exception as e:
        logger.debug(f"bible-api.com error: {e}")
    return None


# ─────────────────────────────────────
# API 2: biblebytopic.com
# Supports: kjv, asv, net, ulb, web
# ─────────────────────────────────────
def _fetch_biblebytopic(ref: str, translation: str) -> str | None:
    book, chapter, verse = _parse_ref(ref)
    if not book:
        return None
    book_num = BOOK_NUMBERS.get(book)
    if not book_num:
        return None
    tl = translation if translation in ["kjv", "asv", "net", "ulb", "web"] else "kjv"
    try:
        url = f"https://biblebytopic.com/api/getverse-{tl}/{book_num}/{chapter}/{verse}"
        r   = requests.get(url, timeout=TIMEOUT, verify=certifi.where())
        if r.status_code == 200:
            text = r.json().get("text", "").strip()
            if text:
                logger.debug(f"✅ biblebytopic: {ref} [{tl}]")
                return text
    except Exception as e:
        logger.debug(f"biblebytopic error: {e}")
    return None


# ─────────────────────────────────────
# API 3: bible.helloao.org
# Supports: 1000+ translations
# ─────────────────────────────────────
def _fetch_helloao(ref: str, translation: str) -> str | None:
    book, chapter, verse = _parse_ref(ref)
    if not book:
        return None
    book_id = HELLOAO_BOOK_IDS.get(book)
    if not book_id:
        return None
    tl = translation.upper()
    try:
        url = f"https://bible.helloao.org/api/{tl}/{book_id}/{chapter}.json"
        r   = requests.get(url, timeout=TIMEOUT, verify=certifi.where())
        if r.status_code == 200:
            data     = r.json()
            verses   = data.get("chapter", {}).get("verses", [])
            verse_int = int(verse)
            for v in verses:
                if v.get("number") == verse_int:
                    text = " ".join(
                        item.get("text", "")
                        for item in v.get("content", [])
                        if isinstance(item, dict)
                    ).strip()
                    if text:
                        logger.debug(f"✅ helloao: {ref} [{tl}]")
                        return text
    except Exception as e:
        logger.debug(f"helloao error: {e}")
    return None


# ─────────────────────────────────────
# API 4: biblesdk.com
# Supports: NET only
# ─────────────────────────────────────
def _fetch_biblesdk(ref: str, translation: str) -> str | None:
    book, chapter, verse = _parse_ref(ref)
    if not book:
        return None
    book_id = HELLOAO_BOOK_IDS.get(book, "").upper()
    if not book_id:
        return None
    try:
        url = f"https://biblesdk.com/api/books/{book_id}/chapters/{chapter}/verses/{verse}"
        r   = requests.get(url, timeout=TIMEOUT, verify=certifi.where())
        if r.status_code == 200:
            text = r.json().get("text", "").strip()
            if text:
                logger.debug(f"✅ biblesdk: {ref}")
                return text
    except Exception as e:
        logger.debug(f"biblesdk error: {e}")
    return None


# ─────────────────────────────────────
# MAIN FETCH — tries APIs in order
# ─────────────────────────────────────
_API_FUNCS = {
    "bible_api_com": _fetch_bible_api_com,
    "biblebytopic":  _fetch_biblebytopic,
    "helloao":       _fetch_helloao,
    "biblesdk":      _fetch_biblesdk,
}

def fetch_verse(ref: str, translation: str = "kjv") -> str | None:
    """
    Try APIs in priority order for the given translation.
    Falls back to next API if one fails.
    Falls back to KJV if translation not found anywhere.
    """
    tl       = translation.lower()
    api_list = TRANSLATION_APIS.get(tl, ["bible_api_com", "helloao"])

    for api_name in api_list:
        fn   = _API_FUNCS.get(api_name)
        if not fn:
            continue
        text = fn(ref, tl)
        if text:
            return text

    # Final fallback — KJV on bible-api.com
    if tl != "kjv":
        logger.warning(f"⚠️ {translation} not found for {ref}, falling back to KJV")
        return _fetch_bible_api_com(ref, "kjv")

    return None
