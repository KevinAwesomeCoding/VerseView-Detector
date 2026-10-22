"""Bounded watcher suggestions and explicit, session-owned manual delivery."""
import copy
import hashlib
import json
import datetime as dt
import logging
import math
import threading
import time
import uuid


class SuggestionError(ValueError):
    pass


class WatcherInbox:
    def __init__(self, engine, running, clock=time.time):
        self.engine, self.running, self.clock = engine, running, clock
        self.lock = threading.RLock()
        self.enabled = self.active = False
        self.generation = 0
        self.rows = []
        self.worker = None

    def prepare(self, enabled):
        with self.lock:
            self.generation += 1
            generation = self.generation
            self.enabled = self.active = bool(enabled)
            self.rows = []
        return lambda suggestion: self.receive(suggestion, generation)

    def receive(self, suggestion, generation):
        # Desktop config requires explicit approval even for high-confidence advice.
        try:
            ref = self.engine._normalize_delivery_reference(suggestion.suggested_reference)
            status = getattr(suggestion.status, 'value', suggestion.status)
            confidence = float(suggestion.confidence)
            if not ref or len(ref) > 128 or self.engine._reject_verse_out_of_range(ref): return
            if status not in ('auto_suggest', 'passive_suggest') or not math.isfinite(confidence): return
            row = dict(id=uuid.uuid4().hex, reference=ref, confidence=min(1, max(0, confidence)),
                       kind=status, stream=suggestion.stream if suggestion.stream in ('primary', 'secondary') else 'unknown',
                       language=suggestion.language if suggestion.language in ('en', 'ml', 'hi', 'multi') else 'und',
                       reasoning=suggestion.reasoning[:400] if isinstance(suggestion.reasoning, str) else '',
                       created_at=dt.datetime.now(dt.timezone.utc).isoformat(), expires_at=self.clock()+90,
                       state='available', candidate_id=None, epoch=getattr(self.engine, '_delivery_epoch', 0))
            with self.lock:
                if generation != self.generation or not self.active: return
                self._expire()
                # Replacing a refreshed suggestion gives it a new identity, so
                # an old displayed button cannot act on changed model advice.
                self.rows = [item for item in self.rows if not (item['reference'] == ref and item['stream'] == row['stream'])]
                self.rows = (self.rows + [row])[-6:]
        except Exception:
            logging.getLogger(__name__).debug('Watcher suggestion projection failed', exc_info=True)

    def _expire(self):
        self.rows = [row for row in self.rows if row['expires_at'] > self.clock() and row['epoch'] == getattr(self.engine, '_delivery_epoch', 0)]

    def revision(self):
        return hashlib.sha256(json.dumps([(r['id'], r['state']) for r in self.rows]).encode()).hexdigest()[:32]

    def select(self, identity):
        with self.lock:
            self._expire()
            row = next((r for r in self.rows if r['id'] == identity and r['state'] == 'available'), None)
            if row is None or not self.active or not self.running():
                raise SuggestionError('Suggestion expired or changed. Review the current inbox.')
            return copy.deepcopy(row)

    def dismiss(self, identity):
        with self.lock:
            self.select(identity)
            self.rows = [r for r in self.rows if r['id'] != identity]

    def clear(self, revision):
        with self.lock:
            self._expire()
            if revision != self.revision() or (self.worker and self.worker.is_alive()):
                raise SuggestionError('Suggestions changed or a send is in progress. Review the current inbox.')
            self.rows = []

    def snapshot(self):
        with self.lock:
            self._expire()
            events = getattr(self.engine, 'get_delivery_events', lambda: [])()
            for row in self.rows:
                latest = next((e for e in reversed(events) if e.get('candidate_id') == row['candidate_id'] and row['candidate_id']), None)
                if latest:
                    row['outcome'] = str(latest.get('outcome', ''))[:64]
                    row['message'] = str(latest.get('reason', ''))[:400]
                    if latest.get('outcome') == 'COMMAND_ACCEPTED': row['state'] = 'accepted'
            status = self.engine.get_watcher_status() if self.enabled else {}
            counts = {key: min(1000000, max(0, status.get(key, 0))) if type(status.get(key)) is int else 0
                      for key in ('cycles', 'suggested', 'discarded')}
            phase = 'off' if not self.enabled else 'stopped' if not self.active or not self.running() else 'scanning' if status.get('scanning') is True else 'configuration_required' if status.get('has_clients') is not True else status.get('cycle_state', 'waiting')
            if phase not in ('off', 'stopped', 'scanning', 'configuration_required', 'waiting', 'suggested', 'failed', 'rate_limited', 'budget_limited'): phase = 'waiting'
            if phase == 'suggested': phase = 'waiting'
            if self.active and self.running() and any(r['state'] == 'available' for r in self.rows): phase = 'suggested'
            return dict(enabled=self.enabled, active=self.active and self.running(), revision=self.revision(), phase=phase,
                        effective_route=status.get('effective_route') if status.get('effective_route') in ('free-profile', 'groq', 'cerebras', 'mistral', 'local') else '',
                        has_clients=status.get('has_clients') is True, **counts,
                        busy=bool(self.worker and self.worker.is_alive()),
                        rows=[{key: copy.deepcopy(value) for key, value in row.items() if key not in ('expires_at', 'epoch')} for row in self.rows])

    def send(self, suggestion_id):
        with self.lock:
            self._expire()
            row = next((item for item in self.rows if item['id'] == suggestion_id and item['state'] == 'available'), None)
            if not self.active or not self.running() or row is None or (self.worker and self.worker.is_alive()):
                raise SuggestionError('Suggestion is stale, unavailable, or another send is in progress.')
            row['state'] = 'sending'
            row['candidate_id'] = uuid.uuid4().hex
            selected = copy.deepcopy(row)
            generation = self.generation
            controller = getattr(self.engine, '_controller', None)
            self.worker = threading.Thread(target=self._send, args=(selected, controller, generation),
                                           name='VerseViewSuggestion', daemon=True)
            self.worker.start()

    def _send(self, selected, controller, generation):
        try:
            with self.lock:
                if generation != self.generation or not self.active: return
            # Use the shared guarded delivery boundary, with no cooldown bypass.
            # A worship/context/Stop epoch change invalidates this request.
            accepted = self.engine.deliver_verse(selected['reference'], controller, bypass_cooldown=False,
                confidence=1.0, source='WATCHER-MANUAL', stream=selected['stream'], candidate_id=selected['candidate_id'], expected_epoch=selected['epoch'])
            with self.lock:
                if generation != self.generation or not self.active or selected['epoch'] != getattr(self.engine, '_delivery_epoch', 0): return
                row = next((item for item in self.rows if item['id'] == selected['id']), None)
                if row: row['state'] = 'accepted' if accepted else 'review'
                if accepted:
                    try:
                        parts = selected['reference'].rsplit(' ', 1)
                        chapter, _, verse = parts[-1].partition(':')
                        self.engine.set_context(parts[0], chapter, verse)
                        self.engine.add_to_verse_history(selected['reference'], source='WATCHER-SUGGESTION')
                    except Exception:
                        # Accepted browser commands remain accepted even if
                        # subsequent context/history bookkeeping fails.
                        logging.getLogger(__name__).exception('Accepted suggestion context update failed')
        except Exception:
            logging.getLogger(__name__).exception('Manual watcher suggestion delivery failed')
            with self.lock:
                if generation != self.generation or not self.active or selected['epoch'] != getattr(self.engine, '_delivery_epoch', 0): return
                row = next((item for item in self.rows if item['id'] == selected['id']), None)
                if row: row['state'] = 'review'

    def cancel(self):
        with self.lock:
            self.active = False
            for row in self.rows:
                if row['state'] == 'sending': row['state'] = 'unknown'

    def join(self):
        # Keep the runtime in Stopping until an owned manual delivery returns.
        # It must not outlive the runtime and touch a newly configured session.
        if self.worker: self.worker.join()
