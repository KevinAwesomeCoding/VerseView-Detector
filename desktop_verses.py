"""Bounded verse tools: local validation, read-only lookup, guarded explicit Send."""
import copy
import datetime as dt
import hashlib
import json
import logging
import re
import threading
import uuid
from parse_reference_eng import BOOK_CHAPTER_COUNTS, BOOKS_ENG
from bible_metadata import verse_count

PAGE_SIZE = 8
MAX_TEXT = 6000


class VerseError(ValueError):
    pass


def book_name(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 64:
        raise VerseError('Choose a Bible book.')
    token = re.sub(r'\s+', '', value.strip().rstrip('.').lower())
    books = list(BOOK_CHAPTER_COUNTS)
    exact = [book for book in books if re.sub(r'\s+', '', book.lower()) == token]
    if exact: return exact[0]
    alias = BOOKS_ENG.get(value.strip().lower())
    if alias in BOOK_CHAPTER_COUNTS: return alias
    matches = [book for book in books if re.sub(r'\s+', '', book.lower()).startswith(token)]
    if len(matches) != 1: raise VerseError('Book name is unknown or ambiguous. Use its full name.')
    return matches[0]


def reference(engine, value, require_verse=False):
    if not isinstance(value, str) or len(value) > 128 or '\x00' in value:
        raise VerseError('Enter a reference such as John 3:16.')
    value = re.sub(r'\b(?:chapter|verse)\s+', '', value.strip(), flags=re.I)
    match = re.fullmatch(r'(.+?)\s+(\d{1,3})(?:\s*[: ,]\s*(\d{1,3}))?', value)
    if not match: raise VerseError('Enter one book and chapter, with an optional verse. Ranges are not supported here.')
    book, chapter = book_name(match[1]), int(match[2])
    verse = int(match[3]) if match[3] else None
    if not 1 <= chapter <= BOOK_CHAPTER_COUNTS[book]: raise VerseError('Chapter is outside this book.')
    if require_verse and verse is None: raise VerseError('Choose a verse before sending.')
    canonical = f'{book} {chapter}' + (f':{verse}' if verse is not None else '')
    bounded = canonical.replace('Psalm ', 'Psalms ', 1)
    count = verse_count(book, chapter) if str(getattr(engine, 'BIBLE_TRANSLATION', '')).lower() == 'kjv' else None
    if verse is not None and count is not None and verse > count: raise VerseError('Verse is outside KJV chapter bounds.')
    if verse is not None and (not 1 <= verse <= 200 or engine._reject_verse_out_of_range(bounded)):
        raise VerseError('Verse is outside the known chapter bounds.')
    return canonical, book, str(chapter), str(verse) if verse is not None else ''


def exact_chapter(book, chapter, translation):
    # Preserve the requested translation. The legacy public wrapper can fall back
    # to KJV, so use its existing transports only where they honor this code.
    from bible_fetcher import _fetch_chapter_helloao, _fetch_chapter_bible_api_com
    rows = _fetch_chapter_helloao(book, chapter, translation)
    if rows: return rows
    if translation in ('kjv', 'web', 'asv', 'oeb', 'webbe', 'clementine', 'almeida', 'rccv'):
        return _fetch_chapter_bible_api_com(book, chapter, translation)
    return []


class VerseTools:
    def __init__(self, runtime, lookup=exact_chapter):
        self.runtime, self.engine, self.lookup = runtime, runtime.engine, lookup
        self.translation = lambda: self.engine.BIBLE_TRANSLATION
        self.lock = threading.RLock()
        self.generation = 0
        self.lookup_worker = self.send_worker = None
        self.selected = self.chapter = self.last_send = self.pending_context = None
        self.cache = {}
        self.message = ''

    def _translation(self):
        value = str(self.translation()).lower()
        if not re.fullmatch(r'[a-z0-9_-]{1,64}', value): raise VerseError('Bible translation is unavailable. Review Settings.')
        return value

    def context(self):
        if self.pending_context:
            value = self.pending_context
        else:
            raw = None
            if self.runtime.state() == 'stopped':
                recovery = getattr(self.runtime, 'recovery', None)
                if recovery and recovery.staged: raw = recovery.staged
                elif recovery and recovery.record and not self.runtime.has_started: raw = recovery.record['data']
            value = {key: (raw.get('current_' + key) if raw else getattr(self.engine, 'current_' + key, None)) or ''
                     for key in ('book', 'chapter', 'verse')}
        value = {key: str(value[key])[:64] for key in ('book', 'chapter', 'verse')}
        revision = hashlib.sha256(json.dumps([value, self.generation, getattr(self.engine, '_delivery_epoch', 0)], sort_keys=True).encode()).hexdigest()[:32]
        return {**value, 'revision': revision, 'staged': self.pending_context is not None}

    def set_context(self, revision, value):
        _, book, chapter, verse = reference(self.engine, value)
        with self.lock:
            if revision != self.context()['revision']: raise VerseError('Context changed. Reload it before applying your edit.')
            if self.send_worker and self.send_worker.is_alive(): raise VerseError('Wait for the current Send before editing context.')
            context = dict(book=book, chapter=chapter, verse=verse)
            if self.runtime.state() == 'running':
                self.engine.set_delivery_mode(worship=self.engine.WORSHIP_MODE, hold=self.engine.DELIVERY_HOLD)
                self.engine.set_context(book, chapter, verse)
                self.pending_context = None
                self.message = 'Context updated. Nothing was presented.'
            elif self.runtime.state() == 'stopped':
                self.pending_context = context
                self.message = 'Context prepared for the next Start. Nothing was presented.'
            else: raise VerseError('Context editing is unavailable while the engine changes state.')

    def prepare_start(self):
        self.cancel()
        if self.pending_context:
            self.engine.set_context(**self.pending_context)
            self.pending_context = None

    def cancel(self):
        with self.lock:
            self.generation += 1
            if self.selected: self.selected['status'] = 'stale'
            if self.chapter: self.chapter['status'] = 'stale'
            if self.last_send and self.last_send['outcome'] == 'SUBMITTED':
                self.last_send.update(outcome='CANCELLED', reason='Engine state changed; inspect delivery activity for any in-flight command.')

    def reset_context(self):
        with self.lock:
            self.pending_context = None
            self.cancel()

    def join(self):
        for worker in (self.lookup_worker, self.send_worker):
            if worker and worker.is_alive(): worker.join()

    def grid_preview(self, revision, value):
        with self.lock:
            grid = self.grid()
            if revision != grid['revision'] or not grid['count']:
                raise VerseError('Chapter changed. Select a verse from the current grid.')
            canonical, _, _, verse = reference(self.engine, value, True)
            if canonical.rsplit(':', 1)[0] != grid['reference'] or int(verse) > grid['count']:
                raise VerseError('Verse is outside the current chapter grid.')
            self.preview(canonical)

    def clear_history(self, revision):
        with self.lock:
            if revision != self.snapshot()['history_revision']:
                raise VerseError('History changed. Review the latest list before clearing it.')
            self.engine.clear_verse_history()
            self.message = 'Current verse history cleared. Saved sessions, sermon references and delivery diagnostics were retained.'

    def grid(self):
        context = self.context()
        count = verse_count(context['book'], context['chapter'])
        return dict(reference=' '.join((context['book'], context['chapter'])).strip(),
                    count=count, current=context['verse'], revision=context['revision'], numbering='KJV',
                    note='KJV numbering. Other translations may omit or renumber verses; preview their text before sending.' if str(self.translation()).lower() != 'kjv' else 'Select a number to preview. Use Send explicitly to present it.')

    def snapshot(self):
        with self.lock:
            try: translation = self._translation()
            except Exception: translation = ''; self.message = 'Bible settings are unavailable. Reconnect before using verse tools.'
            if self.selected and self.selected['translation'] != translation: self.selected['status'] = 'stale'
            if self.chapter and self.chapter['translation'] != translation: self.chapter['status'] = 'stale'
            if self.last_send:
                events = [row for row in self.engine.get_delivery_events() if row.get('candidate_id') == self.last_send['candidate_id']]
                if events:
                    latest = events[-1]
                    self.last_send.update(outcome=latest['outcome'], reason=latest['reason'])
            rows = []
            for item in self.engine.get_verse_history()[-128:]:
                try: canonical, _, _, _ = reference(self.engine, item.get('ref'), True)
                except (ValueError, TypeError): continue
                rows.append({'reference': canonical, 'time': str(item.get('time', ''))[:32]})
            return dict(context=self.context(), grid=self.grid(), history_revision=hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()[:32], translation=translation, message=self.message,
                        books=[{'name': book, 'chapters': count} for book, count in BOOK_CHAPTER_COUNTS.items()],
                        lookup_busy=bool(self.lookup_worker and self.lookup_worker.is_alive()),
                        send_busy=bool(self.send_worker and self.send_worker.is_alive()), history=rows,
                        selected=copy.deepcopy(self.selected), chapter=copy.deepcopy(self.chapter), last_send=copy.deepcopy(self.last_send))

    def preview(self, value, chapter=False, page=0):
        canonical, book, number, verse = reference(self.engine, value, not chapter)
        if type(page) is not int or not 0 <= page <= 24: raise VerseError('Invalid chapter page.')
        with self.lock:
            if self.lookup_worker and self.lookup_worker.is_alive(): raise VerseError('A lookup is still finishing. You can keep listening or close this popup.')
            translation, generation = self._translation(), self.generation
            selected_id = uuid.uuid4().hex
            if chapter:
                self.chapter = dict(reference=f'{book} {number}', translation=translation, page=page, more=False, rows=[], status='loading')
            else:
                self.selected = dict(id=selected_id, reference=canonical, translation=translation, text='', status='loading')
            self.message = ''
            def work():
                try:
                    key = (book, number, translation)
                    rows = self.cache.get(key)
                    if rows is None:
                        raw = self.lookup(book, number, translation)
                        if not isinstance(raw, list) or len(raw) > 200: raise VerseError('Invalid chapter response.')
                        rows = []
                        seen = set()
                        for item in raw:
                            if not isinstance(item, dict): continue
                            n, text = item.get('num'), item.get('text')
                            if type(n) is not int or n in seen or not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT: continue
                            try: reference(self.engine, f'{book} {number}:{n}', True)
                            except VerseError: continue
                            seen.add(n); rows.append({'reference': f'{book} {number}:{n}', 'text': text.strip()})
                        rows.sort(key=lambda item: int(item['reference'].rsplit(':', 1)[1]))
                    with self.lock:
                        if generation != self.generation or translation != self._translation(): return
                        if rows:
                            if len(self.cache) >= 4: self.cache.pop(next(iter(self.cache)))
                            self.cache[key] = rows
                        if chapter:
                            offset = page * PAGE_SIZE
                            self.chapter.update(rows=rows[offset:offset + PAGE_SIZE], more=len(rows) > offset + PAGE_SIZE,
                                                status='ready' if rows else 'unavailable')
                        elif self.selected and self.selected['id'] == selected_id:
                            text = next((row['text'] for row in rows if row['reference'] == canonical), '')
                            self.selected.update(text=text, status='ready' if text else 'unavailable')
                except Exception:
                    with self.lock:
                        if generation == self.generation:
                            target = self.chapter if chapter else self.selected
                            if target: target['status'] = 'unavailable'
                            self.message = 'Text lookup failed. The reference is still validated; no presentation was requested.'
                    logging.getLogger(__name__).exception('Verse preview lookup failed')
            self.lookup_worker = threading.Thread(target=work, name='VerseLookup', daemon=True)
            self.lookup_worker.start()

    def send(self, selection_id):
        with self.lock:
            selected = self.selected
            if (not selected or selection_id != selected['id'] or selected['status'] == 'stale'
                    or selected['translation'] != self._translation()): raise VerseError('Selection changed. Preview it again before sending.')
            if self.runtime.state() != 'running' or self.runtime.stop_requested.is_set(): raise VerseError('Start listening before sending a reference.')
            if self.send_worker and self.send_worker.is_alive(): raise VerseError('A Send is already in progress. No retry was made.')
            canonical, _, _, _ = reference(self.engine, selected['reference'], True)
            generation, epoch = self.generation, self.engine._delivery_epoch
            candidate_id = uuid.uuid4().hex
            self.last_send = dict(reference=canonical, candidate_id=candidate_id, outcome='SUBMITTED', reason='Waiting for the delivery checks.')
            controller = getattr(self.engine, '_controller', None)
            def work():
                try:
                    if generation != self.generation or self.runtime.stop_requested.is_set(): return
                    accepted = self.engine.deliver_verse(canonical, controller, bypass_cooldown=False, confidence=1.0,
                        source='DESKTOP-MANUAL', stream='unknown', candidate_id=candidate_id, expected_epoch=epoch)
                    with self.lock:
                        if self.last_send and self.last_send['candidate_id'] == candidate_id:
                            self.last_send.update(outcome='COMMAND_ACCEPTED' if accepted else 'NOT_ACCEPTED',
                                reason='Command accepted; visible VerseVIEW output is unverified.' if accepted else 'Not accepted by the delivery checks. Inspect the reference outcome.')
                except Exception:
                    with self.lock:
                        if self.last_send and self.last_send['candidate_id'] == candidate_id:
                            self.last_send.update(outcome='ERROR', reason='Send failed. Check delivery activity before trying again.')
                    logging.getLogger(__name__).exception('Guarded manual verse send failed')
            self.send_worker = threading.Thread(target=work, name='VerseSend', daemon=True)
            self.send_worker.start()
