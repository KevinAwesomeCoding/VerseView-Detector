# -*- coding: utf-8 -*-
"""
contextual_watcher.py  —  Contextual Verse Watcher  (PART 1 of 3)
================================================================================

A continuous, *parallel* scripture watcher that runs ALONGSIDE the existing
fast-path detection pipeline (regex parser → contextual matcher → LLM fallback),
never instead of it.

Where the fast path answers "did the speaker just say an explicit reference
(Book Chapter:Verse)?", this watcher answers a softer question by reasoning over
a rolling window of recent speech with an LLM:

    "Is the speaker referencing scripture right now — even indirectly, through
     paraphrase or partial quotation — and if so, which passage?"

It is deliberately self-contained:
  • It imports NOTHING from vv_streaming_master (no circular import).
  • The LLM clients, the per-stream languages and the delivery callback are all
    injected from the outside in Part 2. Any object exposing the same
    `.chat.completions.create(model=, messages=, temperature=, max_tokens=)`
    surface as the existing _GroqClient / _CerebrasClient works unchanged.
  • No GUI code. No settings persistence. Every tunable is a hardcoded default
    marked  # TODO(Part 3)  so Part 3 can lift it into settings.py without
    touching the logic.

Part 2 wires this in; Part 3 makes the defaults configurable. See the bottom of
this file for the exhaustive list of Part-3 settings and the public interface
Part 2 will call.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Deque, Optional

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
#  TUNABLE DEFAULTS  (Part 3: now the field defaults of WatcherConfig below)
#
#  These module constants are the single source of default truth. The GUI in
#  Part 3 overrides a subset of them per-session by passing a WatcherConfig built
#  from settings.py; the rest keep these defaults. This module still NEVER reads
#  settings.py itself — the engine builds the WatcherConfig and injects it.
# ══════════════════════════════════════════════════════════════════════════════

# ── Master switch (Part 3 GUI: default OFF — experimental, opt-in only) ────────
WATCHER_ENABLED_DEFAULT = False

# ── Rolling context buffer bounds (trim whichever limit is hit first) ─────────
CTX_MAX_LINES        = 10     # Part-3 GUI: rolling window size (lines)
CTX_MAX_AGE_SEC      = 40.0   # Part-3 GUI: rolling window size (seconds)

# ── Batching / trigger (call the LLM on a timer OR after enough new speech) ───
LLM_INTERVAL_SEC     = 5.0    # Part-3 GUI: batch interval — fire at least this often per stream
NEW_WORDS_TRIGGER    = 25     # …or sooner, once this many new words arrive
NEW_LINES_TRIGGER    = 3      # …or sooner, once this many new finals arrive
MIN_DISPATCH_GAP_SEC = 2.5    # never fire two cycles closer than this (per stream)
MIN_WORDS_TO_REASON  = 6      # don't bother the LLM with < this many words
TICK_INTERVAL_SEC    = 1.0    # how often the async driver re-checks due streams

# ── LLM request shape ─────────────────────────────────────────────────────────
LLM_TEMPERATURE      = 0.1    # low → deterministic JSON
LLM_MAX_TOKENS       = 220    # enough for the JSON object, no more
LLM_TIMEOUT_SEC      = 20.0   # soft cap so a hung call can't stall the loop
PRIMARY_MODEL        = "llama-3.1-8b-instant"  # Groq fast model (mirrors extract_verse_with_llm)
FALLBACK_MODEL       = "llama3.1-8b"           # Cerebras small model (mirrors _llm_semantic_match)

# ── Deduplication ─────────────────────────────────────────────────────────────
DEDUP_COOLDOWN_SEC   = 60.0   # Part-3 GUI: suppress a repeat of the same ref within this window
DEDUP_HISTORY_LEN    = 8      # remember the last N suggested refs per stream
CONF_RISE_DELTA      = 0.15   # …unless confidence rose by at least this much

# ── Confidence gating ─────────────────────────────────────────────────────────
CONF_HIGH            = 0.85   # Part-3 GUI: auto-suggest threshold — ≥ this (no conflict) → AUTO_SUGGEST
CONF_MEDIUM          = 0.60   # Part-3 GUI: passive threshold — ≥ this → PASSIVE_SUGGEST; below → DISCARD
FASTPATH_CONFLICT_SEC = 30.0  # a *different* fast-path ref this recent = a conflict


# ══════════════════════════════════════════════════════════════════════════════
#  WATCHER CONFIG  —  the full tunable surface, injected by the engine (Part 3)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class WatcherConfig:
    """Every runtime tunable for the watcher in one place.

    Field defaults mirror the module constants above, so a bare ``WatcherConfig()``
    reproduces the pre-Part-3 behaviour exactly (except ``enabled`` which is now
    OFF by default — the feature is opt-in). The engine constructs one of these
    from settings.py each session and passes it in; the module itself never reads
    settings. Six fields are surfaced in the Part-3 GUI (marked GUI below); the
    rest stay internal with sensible defaults.

    ``__post_init__`` clamps values to safe ranges so a bad hand-entered setting
    (e.g. a 0-second interval, or auto-threshold below the passive one) can never
    put the watcher into a pathological state.
    """
    enabled:               bool  = WATCHER_ENABLED_DEFAULT   # GUI: master toggle (default OFF)
    provider:              str   = "groq"                    # GUI: provider label (routing done by engine)
    primary_model:         str   = PRIMARY_MODEL
    fallback_model:        str   = FALLBACK_MODEL

    # batching
    llm_interval_sec:      float = LLM_INTERVAL_SEC          # GUI: batch interval (s)
    new_words_trigger:     int   = NEW_WORDS_TRIGGER
    new_lines_trigger:     int   = NEW_LINES_TRIGGER
    min_dispatch_gap_sec:  float = MIN_DISPATCH_GAP_SEC
    min_words_to_reason:   int   = MIN_WORDS_TO_REASON
    tick_interval_sec:     float = TICK_INTERVAL_SEC

    # rolling window
    ctx_max_lines:         int   = CTX_MAX_LINES             # GUI: window size (lines)
    ctx_max_age_sec:       float = CTX_MAX_AGE_SEC           # GUI: window size (seconds)

    # llm request
    llm_temperature:       float = LLM_TEMPERATURE
    llm_max_tokens:        int   = LLM_MAX_TOKENS
    llm_timeout_sec:       float = LLM_TIMEOUT_SEC

    # dedup
    dedup_cooldown_sec:    float = DEDUP_COOLDOWN_SEC        # GUI: cooldown window (s)
    dedup_history_len:     int   = DEDUP_HISTORY_LEN
    conf_rise_delta:       float = CONF_RISE_DELTA

    # gating
    conf_high:             float = CONF_HIGH                 # GUI: auto-suggest confidence
    conf_medium:           float = CONF_MEDIUM              # GUI: passive-suggest confidence
    fastpath_conflict_sec: float = FASTPATH_CONFLICT_SEC

    def __post_init__(self):
        # Clamp everything into safe ranges — never trust hand-entered numbers.
        self.enabled              = bool(self.enabled)
        self.llm_interval_sec     = max(1.0, float(self.llm_interval_sec))
        self.new_words_trigger    = max(1, int(self.new_words_trigger))
        self.new_lines_trigger    = max(1, int(self.new_lines_trigger))
        self.min_dispatch_gap_sec = max(0.5, float(self.min_dispatch_gap_sec))
        self.min_words_to_reason  = max(1, int(self.min_words_to_reason))
        self.tick_interval_sec    = max(0.25, float(self.tick_interval_sec))
        self.ctx_max_lines        = max(1, int(self.ctx_max_lines))
        self.ctx_max_age_sec      = max(5.0, float(self.ctx_max_age_sec))
        self.llm_max_tokens       = max(32, int(self.llm_max_tokens))
        self.llm_timeout_sec      = max(2.0, float(self.llm_timeout_sec))
        self.dedup_cooldown_sec   = max(0.0, float(self.dedup_cooldown_sec))
        self.dedup_history_len    = max(1, int(self.dedup_history_len))
        # Confidences into [0,1]; keep auto ≥ passive so the gating bands are sane.
        self.conf_medium = min(1.0, max(0.0, float(self.conf_medium)))
        self.conf_high   = min(1.0, max(0.0, float(self.conf_high)))
        if self.conf_high < self.conf_medium:
            self.conf_high = self.conf_medium


# ══════════════════════════════════════════════════════════════════════════════
#  RESULT TYPES
# ══════════════════════════════════════════════════════════════════════════════

class WatcherStatus(str, Enum):
    """Confidence-gating decision for a single watcher cycle.

    The GUI wiring in Part 2 keys off this enum:
      • AUTO_SUGGEST    — high confidence, no conflicting fast-path result;
                          safe to surface prominently / pre-stage.
      • PASSIVE_SUGGEST — medium confidence (or high but conflicting / ref-less);
                          show quietly as a hint, never act automatically.
      • DISCARD         — low confidence, is_reference false, deduped, or unusable;
                          the loop drops it and does NOT call on_suggestion.
    """
    AUTO_SUGGEST    = "auto_suggest"
    PASSIVE_SUGGEST = "passive_suggest"
    DISCARD         = "discard"


@dataclass
class WatcherSuggestion:
    """One evaluated watcher cycle, handed to the on_suggestion callback (Part 2).

    Everything the GUI needs is here — no need to reach back into the watcher.
    """
    stream:              str            # "primary" | "secondary"
    language:            str            # "en" | "hi" | "ml" | "multi"
    is_reference:        bool
    confidence:          float          # 0.0–1.0
    suggested_reference: Optional[str]  # "Book Chapter:Verse" / "Book Chapter" / None
    reasoning:           str
    explicit_or_implied: str            # "explicit" | "implied" | "none"
    status:              WatcherStatus
    window_text:         str            # the transcript window the LLM reasoned over
    created_at:          float
    raw:                 dict           # the parsed JSON, verbatim, for debugging


# ══════════════════════════════════════════════════════════════════════════════
#  ROLLING CONTEXT BUFFER  (one per STT stream)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class _Line:
    ts:   float
    text: str


class _RollingContextBuffer:
    """A bounded, time-and-count-limited window of recent transcript finals for a
    single STT stream.

    Two independent bounds are enforced on every append, and whichever is hit
    first wins (both come from WatcherConfig.ctx_max_lines / ctx_max_age_sec):
      • at most `max_lines` lines, and
      • no line older than `max_age_sec` seconds.

    Separately, two *monotonic* counters (total words / lines ever fed) are kept
    so the batching trigger can ask "how much NEW speech since the last LLM
    dispatch?" without being fooled by trimming — trimming shrinks the window but
    never rewinds the counters.
    """

    def __init__(self, max_lines: int = CTX_MAX_LINES,
                 max_age_sec: float = CTX_MAX_AGE_SEC,
                 clock: Callable[[], float] = time.time):
        self._lines:      Deque[_Line] = deque()
        self._max_lines   = max_lines
        self._max_age_sec = max_age_sec
        self._now         = clock
        # Monotonic totals — never decrease, survive trimming.
        self.total_words  = 0
        self.total_lines  = 0

    def add(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        now = self._now()
        self._lines.append(_Line(now, text))
        self.total_words += len(text.split())
        self.total_lines += 1
        self._trim(now)

    def _trim(self, now: float) -> None:
        # Age bound first, then the hard line-count cap.
        while self._lines and (now - self._lines[0].ts) > self._max_age_sec:
            self._lines.popleft()
        while len(self._lines) > self._max_lines:
            self._lines.popleft()

    def window_text(self) -> str:
        """The current window as a single newline-joined string for the LLM."""
        # Trim on read too, so a stream that has gone quiet doesn't hand the LLM
        # a stale window built entirely from >max_age-old speech.
        self._trim(self._now())
        return "\n".join(l.text for l in self._lines)

    def window_word_count(self) -> int:
        self._trim(self._now())
        return sum(len(l.text.split()) for l in self._lines)

    def clear(self) -> None:
        self._lines.clear()
        # NOTE: totals intentionally NOT reset here — reset() on the watcher owns
        # a full stream reset; clear() only empties the visible window.


# ══════════════════════════════════════════════════════════════════════════════
#  PER-STREAM STATE
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class _StreamState:
    role:     str                    # "primary" | "secondary"
    language: str                    # "en" | "hi" | "ml" | "multi"
    buffer:   _RollingContextBuffer

    # Batching bookkeeping (rebaselined at each dispatch).
    last_dispatch_ts:    float = 0.0
    words_at_dispatch:   int   = 0
    lines_at_dispatch:   int   = 0
    in_flight:           bool  = False

    # Deduplication: recent (ref, ts, confidence) that were actually emitted.
    # maxlen is set explicitly at construction from WatcherConfig.dedup_history_len;
    # this default_factory is only a fallback for a bare _StreamState().
    recent: Deque = field(default_factory=lambda: deque(maxlen=DEDUP_HISTORY_LEN))

    # Latest fast-path reference seen for this stream (fed by Part 2), for
    # conflict detection during confidence gating.
    fastpath_ref:  Optional[str] = None
    fastpath_ts:   float         = 0.0


# ══════════════════════════════════════════════════════════════════════════════
#  THE WATCHER
# ══════════════════════════════════════════════════════════════════════════════

class ContextualVerseWatcher:
    """Continuous, parallel, per-stream contextual scripture watcher.

    Lifecycle (Part 2 will drive this):
        w = ContextualVerseWatcher(
                primary_client=groq_client,
                fallback_client=cerebras_client,
                primary_language="ml", secondary_language="en",
                on_suggestion=my_gui_callback,
            )
        # inside the engine's asyncio setup, alongside live_points_loop():
        watcher_task = asyncio.create_task(w.run(stop_event))

        # inside create_transcript_handler finals:
        w.feed(sentence, is_secondary=is_secondary)

        # whenever the fast path emits a verse (for conflict gating):
        w.note_fastpath_reference("John 3:16", is_secondary=False)

    Threading model:
      • feed() and note_fastpath_reference() are called from STT provider
        threads / callbacks. They only touch buffers + counters under a lock and
        return instantly — they NEVER call the LLM, so the live transcript path
        is never blocked or slowed.
      • run() lives on the engine's asyncio loop. It ticks every
        config.tick_interval_sec, decides which streams are "due", and offloads
        the blocking LLM call to a thread executor (like live_points_loop).
      • on_suggestion fires on the engine loop's executor-callback context; Part
        2 is responsible for marshalling to the GUI thread.
    """

    def __init__(
        self,
        *,
        primary_client=None,
        fallback_client=None,
        primary_language: str = "en",
        secondary_language: Optional[str] = None,
        on_suggestion: Optional[Callable[[WatcherSuggestion], None]] = None,
        config: Optional[WatcherConfig] = None,
        primary_model: Optional[str] = None,
        fallback_model: Optional[str] = None,
        clock: Callable[[], float] = time.time,
        log: Optional[logging.Logger] = None,
    ):
        self._cfg             = config or WatcherConfig()
        self._primary_client  = primary_client
        self._fallback_client = fallback_client
        # Explicit model kwargs (if given) win over the config's; otherwise the
        # config supplies them. Keeps Part-2 call sites working unchanged.
        self._primary_model   = primary_model  or self._cfg.primary_model
        self._fallback_model  = fallback_model or self._cfg.fallback_model
        self._on_suggestion   = on_suggestion
        self._now             = clock
        self._log             = log or logger

        self.enabled          = self._cfg.enabled   # bound to the settings toggle
        self._lock            = threading.Lock()

        # ── Activity heartbeat (for a visible "is it running?" status in the GUI) ─
        # Every reasoning cycle records here so the panel can show a live pulse
        # (checks counter + last-check time + last outcome) rather than silence.
        self._stats_lock = threading.Lock()
        self._stats = {
            "cycles":        0,      # total LLM reasoning cycles run
            "last_cycle_ts": 0.0,    # wall-clock of the most recent cycle
            "suggested":     0,      # cycles that produced an AUTO/PASSIVE suggestion
            "discarded":     0,      # cycles read but gated out (low conf / no ref)
            "last_status":   "",     # short human summary of the most recent cycle
        }

        # One stream state per active STT role. The secondary is only created
        # when a secondary language is supplied (mirrors DUAL_STT_ENABLED).
        self._streams: dict[str, _StreamState] = {
            "primary": self._make_stream("primary", primary_language or "en"),
        }
        if secondary_language:
            self._streams["secondary"] = self._make_stream("secondary", secondary_language)

    def _make_stream(self, role: str, language: str) -> _StreamState:
        """Build a per-stream state whose buffer bounds and dedup history length
        come from the active config."""
        return _StreamState(
            role=role,
            language=language or "en",
            buffer=_RollingContextBuffer(
                max_lines=self._cfg.ctx_max_lines,
                max_age_sec=self._cfg.ctx_max_age_sec,
                clock=self._now,
            ),
            recent=deque(maxlen=self._cfg.dedup_history_len),
        )

    # ── Public: configuration hooks (Part 2/3) ────────────────────────────────

    def set_languages(self, primary_language: str,
                       secondary_language: Optional[str] = None) -> None:
        """Re-declare which language each stream is transcribing. Safe to call at
        session (re)configure; keeps the same per-stream distinction the rest of
        the app already tracks via PRIMARY_LANGUAGE / SECONDARY_LANGUAGE."""
        with self._lock:
            self._streams["primary"].language = primary_language or "en"
            if secondary_language:
                if "secondary" not in self._streams:
                    self._streams["secondary"] = self._make_stream("secondary", secondary_language)
                else:
                    self._streams["secondary"].language = secondary_language
            else:
                self._streams.pop("secondary", None)

    def set_clients(self, primary_client=None, fallback_client=None) -> None:
        """Swap the injected LLM clients (e.g. after a re-configure with new keys)."""
        self._primary_client  = primary_client
        self._fallback_client = fallback_client

    def set_on_suggestion(self, cb: Optional[Callable[[WatcherSuggestion], None]]) -> None:
        self._on_suggestion = cb

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)

    def set_config(self, config: WatcherConfig) -> None:
        """Replace the live config and re-apply the bounds that affect existing
        streams (buffer size/age, dedup history length). Model names follow too."""
        self._cfg = config or WatcherConfig()
        self.enabled         = self._cfg.enabled
        self._primary_model  = self._cfg.primary_model
        self._fallback_model = self._cfg.fallback_model
        with self._lock:
            for st in self._streams.values():
                st.buffer = _RollingContextBuffer(
                    max_lines=self._cfg.ctx_max_lines,
                    max_age_sec=self._cfg.ctx_max_age_sec,
                    clock=self._now,
                )
                st.recent = deque(maxlen=self._cfg.dedup_history_len)

    def reset(self) -> None:
        """Full reset for a new session: empty every buffer, clear dedup history
        and batching baselines. Language/client wiring is preserved."""
        with self._lock:
            for st in self._streams.values():
                st.buffer = _RollingContextBuffer(
                    max_lines=self._cfg.ctx_max_lines,
                    max_age_sec=self._cfg.ctx_max_age_sec,
                    clock=self._now,
                )
                st.last_dispatch_ts  = 0.0
                st.words_at_dispatch = 0
                st.lines_at_dispatch = 0
                st.in_flight         = False
                st.recent            = deque(maxlen=self._cfg.dedup_history_len)
                st.fastpath_ref = None
                st.fastpath_ts  = 0.0

    # ── Public: fast, non-blocking inputs (called from STT threads) ───────────

    def feed(self, text: str, is_secondary: bool = False) -> None:
        """Append a final transcript line to the appropriate stream's rolling
        buffer. Returns immediately; never calls the LLM.

        Part 2 calls this from the FINAL branch of create_transcript_handler /
        create_sarvam_transcript_handler, passing the same is_secondary flag the
        handler already carries."""
        role = "secondary" if is_secondary else "primary"
        with self._lock:
            st = self._streams.get(role)
            if st is None:
                # Secondary fed while dual-STT is off, or before set_languages —
                # ignore rather than inventing an untracked stream.
                return
            st.buffer.add(text)

    def note_fastpath_reference(self, ref: str, is_secondary: bool = False) -> None:
        """Record the most recent reference the EXISTING fast path produced for a
        stream. Used only by confidence gating to detect conflicts — the watcher
        never mutates or drives the fast path. Part 2 calls this wherever the
        regex/contextual path presents a verse."""
        if not ref:
            return
        role = "secondary" if is_secondary else "primary"
        with self._lock:
            st = self._streams.get(role)
            if st is None:
                return
            st.fastpath_ref = ref.strip()
            st.fastpath_ts  = self._now()

    # ── Public: activity status (for a live "is it running?" GUI indicator) ───

    def status(self) -> dict:
        """Return a snapshot of the watcher's live activity so the GUI can show
        whether it's actually reading — enabled state, whether an LLM client is
        wired, the number of reasoning cycles run, the last cycle time, and a
        short summary of the last outcome. Cheap and lock-guarded; safe to poll."""
        with self._stats_lock:
            snap = dict(self._stats)
        snap["enabled"]     = self.enabled
        snap["has_clients"] = bool(self._primary_client or self._fallback_client)
        snap["provider"]    = self._cfg.provider
        snap["streams"]     = list(self._streams.keys())
        return snap

    def _record_cycle(self, status_text: str, *, suggested: bool = False,
                      discarded: bool = False) -> None:
        """Update the activity heartbeat after each reasoning cycle."""
        with self._stats_lock:
            self._stats["cycles"]       += 1
            self._stats["last_cycle_ts"] = self._now()
            self._stats["last_status"]   = status_text
            if suggested:
                self._stats["suggested"] += 1
            if discarded:
                self._stats["discarded"] += 1

    # ── Public: the async driver (lives on the engine loop) ───────────────────

    async def run(self, stop_event) -> None:
        """Long-running driver. Ticks on config.tick_interval_sec, dispatches an
        LLM cycle for each due stream, and never lets an exception escape (a crash
        here must not take down the engine loop or the STT streams)."""
        loop = asyncio.get_event_loop()
        self._log.info("🔭 Contextual Verse Watcher started")
        try:
            while not stop_event.is_set():
                try:
                    await asyncio.sleep(self._cfg.tick_interval_sec)
                except asyncio.CancelledError:
                    break
                if not self.enabled:
                    continue
                try:
                    for role, snap in self._collect_due_streams():
                        # Fire-and-forget per stream; primary & secondary are
                        # independent and may reason concurrently.
                        asyncio.ensure_future(self._run_cycle(role, snap, loop))
                except Exception as e:  # defensive: a tick must never kill the loop
                    self._log.debug(f"🔭 watcher tick error: {e}")
        finally:
            self._log.info("🔭 Contextual Verse Watcher stopped")

    # ── Internal: batching decision ───────────────────────────────────────────

    def _collect_due_streams(self):
        """Return a list of (role, snapshot) for streams that should fire this
        tick, rebaselining their batching counters *now* so the timer/word
        triggers reset immediately (and the in-flight guard prevents overlap)."""
        due = []
        now = self._now()
        with self._lock:
            for role, st in self._streams.items():
                if st.in_flight:
                    continue

                words_now = st.buffer.total_words
                lines_now = st.buffer.total_lines
                new_words = words_now - st.words_at_dispatch
                new_lines = lines_now - st.lines_at_dispatch

                if new_words <= 0:
                    continue  # nothing new — don't re-reason identical content
                if st.buffer.window_word_count() < self._cfg.min_words_to_reason:
                    continue  # too little context to be worth a call

                since_last = now - st.last_dispatch_ts
                if since_last < self._cfg.min_dispatch_gap_sec:
                    continue  # burst guard

                due_by_timer  = since_last >= self._cfg.llm_interval_sec
                due_by_volume = (new_words >= self._cfg.new_words_trigger
                                 or new_lines >= self._cfg.new_lines_trigger)
                if not (due_by_timer or due_by_volume):
                    continue

                # Reserve this slot: rebaseline + mark in-flight under the lock.
                st.in_flight         = True
                st.last_dispatch_ts  = now
                st.words_at_dispatch = words_now
                st.lines_at_dispatch = lines_now

                due.append((role, _Snapshot(
                    role=role,
                    language=st.language,
                    window_text=st.buffer.window_text(),
                )))
        return due

    # ── Internal: one full LLM cycle ──────────────────────────────────────────

    async def _run_cycle(self, role: str, snap: "_Snapshot", loop) -> None:
        raw_text = None
        try:
            raw_text = await asyncio.wait_for(
                loop.run_in_executor(None, self._call_llm, snap),
                timeout=self._cfg.llm_timeout_sec,
            )
        except asyncio.TimeoutError:
            self._log.debug(f"🔭 watcher LLM timed out ({role}) — cycle skipped")
        except Exception as e:
            self._log.debug(f"🔭 watcher LLM error ({role}): {e} — cycle skipped")
        finally:
            self._clear_in_flight(role)

        if not raw_text:
            # No usable reply (no client wired / timeout / provider error /
            # rate-limited). Still a "cycle" for heartbeat purposes so the GUI
            # can show the watcher IS trying even when the LLM isn't answering.
            self._record_cycle("no LLM response — check API key / rate limit")
            return

        parsed = self._parse_json(raw_text)
        if parsed is None:
            # Parsing failed → log + discard this cycle silently (per spec).
            self._log.debug(f"🔭 watcher: unparseable LLM reply ({role}) — cycle discarded")
            self._record_cycle("read, but reply was unreadable")
            return

        result = self._evaluate(role, snap, parsed)
        if result is None:
            self._record_cycle("read, no result")
            return
        if result.status is WatcherStatus.DISCARD:
            self._log.debug(
                f"🔭 watcher DISCARD ({role}): "
                f"ref={result.suggested_reference!r} conf={result.confidence:.2f} "
                f"reason={result.reasoning[:60]!r}"
            )
            _ref = result.suggested_reference
            self._record_cycle(
                (f"read {_ref} (low confidence)" if _ref else "read, no reference found"),
                discarded=True,
            )
            return
        self._record_cycle(f"suggested {result.suggested_reference}", suggested=True)
        self._emit(result)

    def _clear_in_flight(self, role: str) -> None:
        with self._lock:
            st = self._streams.get(role)
            if st is not None:
                st.in_flight = False

    # ── Internal: the blocking LLM call (runs in an executor thread) ──────────

    def _call_llm(self, snap: "_Snapshot") -> Optional[str]:
        """Reuse the injected Groq/Cerebras-style clients. Primary first, then
        fallback. Returns the raw reply string, or None on any failure. Runs OFF
        the event loop so it can never stall STT."""
        system = self._system_prompt(snap.language)
        user   = self._user_prompt(snap.window_text)
        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ]
        # Item 5: estimate prompt tokens up front so usage is visible even if the
        # call later fails (helps spot a runaway window during a live service).
        prompt_tok = self._estimate_tokens(system) + self._estimate_tokens(user)

        attempts = []
        if self._primary_client:
            attempts.append((self._primary_client, self._primary_model, "primary"))
        if self._fallback_client:
            attempts.append((self._fallback_client, self._fallback_model, "fallback"))
        if not attempts:
            return None

        for client, model, tag in attempts:
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=self._cfg.llm_temperature,
                    max_tokens=self._cfg.llm_max_tokens,
                )
                content = resp.choices[0].message.content
                # Item 5: debug-level estimated token usage per successful call.
                # These clients don't surface provider `usage`, so we estimate
                # ~4 chars/token — good enough for monitoring cost during a
                # service. cap is the configured max_tokens ceiling.
                completion_tok = self._estimate_tokens(content or "")
                self._log.debug(
                    f"🔭 watcher LLM usage [{tag}/{model}] "
                    f"est_tokens prompt≈{prompt_tok} completion≈{completion_tok} "
                    f"total≈{prompt_tok + completion_tok} "
                    f"(window={len(snap.window_text)} chars, cap={self._cfg.llm_max_tokens})"
                )
                if content and content.strip():
                    return content
            except Exception as e:
                # Includes Cerebras' own circuit-breaker RuntimeError — just move
                # on; a skipped cycle is harmless.
                self._log.debug(f"🔭 watcher {tag} client failed: {e}")
                continue
        return None

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Rough token estimate (~4 chars/token) for debug usage logging only.
        Not exact — providers tokenise differently — but stable enough to watch
        cost trends across a live service without pulling in a tokenizer dep."""
        if not text:
            return 0
        return max(1, (len(text) + 3) // 4)

    # ── Internal: prompts (bilingual-aware) ───────────────────────────────────

    _JSON_CONTRACT = (
        'Respond with ONLY a single minified JSON object and nothing else — no '
        'prose, no markdown, no code fences. The object MUST have exactly these '
        'keys:\n'
        '{"is_reference": <true|false>, "confidence": <number 0..1>, '
        '"suggested_reference": <"Book Chapter:Verse" or "Book Chapter" or null>, '
        '"reasoning": <short string, one sentence>, '
        '"explicit_or_implied": <"explicit"|"implied"|"none">}\n'
        'Rules: set is_reference=false (and suggested_reference=null, '
        'explicit_or_implied="none") unless the speaker is clearly pointing at '
        'one identifiable passage. Use "explicit" when a book/chapter/verse is '
        'actually named or read aloud; use "implied" when you inferred the '
        'passage from a quotation or paraphrase. Be conservative: generic '
        'religious language, worship phrases, or broad themes are NOT references.'
    )

    def _system_prompt(self, language: str) -> str:
        if (language or "").lower().startswith("ml"):
            # Malayalam-aware variant — reuses the same "ml" language distinction
            # the dual-STT path already tracks.
            return (
                "You are a scripture-reference detector embedded in a LIVE "
                "Malayalam sermon transcription system. The speaker preaches in "
                "Malayalam and frequently code-switches into English; the "
                "transcript window you receive may be Malayalam, transliterated "
                "Manglish, English translation, or a mix. Malayalam Bible book "
                "names, spoken numerals, and paraphrase are all common. Read the "
                "rolling window of recent speech and decide whether the speaker "
                "is referencing a specific Bible passage right now — by explicit "
                "citation, quotation, or clear paraphrase / partial quotation. "
                "Always give suggested_reference using the ENGLISH book name in "
                "'Book Chapter:Verse' form.\n\n" + self._JSON_CONTRACT
            )
        # English (default; also covers hi/multi — English book names, English JSON).
        return (
            "You are a scripture-reference detector embedded in a LIVE sermon "
            "transcription system. Read the rolling window of the most recent "
            "transcript lines and decide whether the speaker is referencing a "
            "specific Bible passage right now — whether by explicit citation "
            "('John 3:16', 'the book of Romans chapter 8'), by direct quotation, "
            "or by clear paraphrase / partial quotation of one identifiable "
            "verse. Ignore generic religious language and broad themes that do "
            "not point to a single passage.\n\n" + self._JSON_CONTRACT
        )

    @staticmethod
    def _user_prompt(window_text: str) -> str:
        return (
            "Most recent transcript window (oldest line first):\n"
            "-----\n"
            f"{window_text}\n"
            "-----\n"
            "Return the JSON object now."
        )

    # ── Internal: strict JSON parsing (never regex-scrape prose) ──────────────

    def _parse_json(self, text: str) -> Optional[dict]:
        """Deterministically parse the LLM reply as JSON. Tolerates surrounding
        markdown fences and leading/trailing prose by isolating the outermost
        {...} object, but the ANSWER itself is only ever read from parsed JSON —
        we never regex a reference out of a prose reply. Returns a normalised
        dict, or None if it cannot be parsed / is missing is_reference."""
        if not text:
            return None
        s = text.strip()

        # Strip a ```json … ``` or ``` … ``` fence if present.
        if s.startswith("```"):
            s = s.strip("`").strip()
            if s[:4].lower() == "json":
                s = s[4:].strip()

        obj = None
        try:
            obj = json.loads(s)
        except Exception:
            i, j = s.find("{"), s.rfind("}")
            if i != -1 and j != -1 and j > i:
                try:
                    obj = json.loads(s[i:j + 1])
                except Exception:
                    obj = None
        if not isinstance(obj, dict):
            return None
        if "is_reference" not in obj:
            return None  # contract violated → treat as a failed parse

        return self._normalise(obj)

    @staticmethod
    def _normalise(obj: dict) -> Optional[dict]:
        """Coerce parsed JSON into strict, safe types. Returns None if a value is
        so malformed it can't be coerced (treated as a failed cycle)."""
        try:
            is_ref = bool(obj.get("is_reference"))

            try:
                conf = float(obj.get("confidence", 0.0))
            except (TypeError, ValueError):
                conf = 0.0
            conf = max(0.0, min(1.0, conf))

            ref = obj.get("suggested_reference")
            if isinstance(ref, str):
                ref = ref.strip() or None
            elif ref is not None:
                ref = None  # numbers/lists/objects are not valid references

            reasoning = obj.get("reasoning", "")
            reasoning = str(reasoning).strip() if reasoning is not None else ""

            eoi = str(obj.get("explicit_or_implied", "none")).strip().lower()
            if eoi not in ("explicit", "implied", "none"):
                eoi = "none"

            return {
                "is_reference":        is_ref,
                "confidence":          conf,
                "suggested_reference": ref,
                "reasoning":           reasoning,
                "explicit_or_implied": eoi,
            }
        except Exception:
            return None

    # ── Internal: confidence gating + dedup → WatcherSuggestion ───────────────

    def _evaluate(self, role: str, snap: "_Snapshot", parsed: dict) -> Optional[WatcherSuggestion]:
        now         = self._now()
        is_ref      = parsed["is_reference"]
        confidence  = parsed["confidence"]
        ref         = parsed["suggested_reference"]

        status = self._gate(role, ref, is_ref, confidence, now)

        # Deduplication only matters for something we would actually surface.
        if status is not WatcherStatus.DISCARD and ref:
            if not self._dedup_ok(role, ref, confidence, now):
                status = WatcherStatus.DISCARD
            else:
                self._record_emitted(role, ref, confidence, now)

        return WatcherSuggestion(
            stream=role,
            language=snap.language,
            is_reference=is_ref,
            confidence=confidence,
            suggested_reference=ref,
            reasoning=parsed["reasoning"],
            explicit_or_implied=parsed["explicit_or_implied"],
            status=status,
            window_text=snap.window_text,
            created_at=now,
            raw=parsed,
        )

    def _gate(self, role: str, ref: Optional[str], is_ref: bool,
              confidence: float, now: float) -> WatcherStatus:
        """Pure gating decision (no dedup):
            high conf + a ref + no conflicting fast-path result → AUTO_SUGGEST
            medium conf (or high-but-conflicting / ref-less)     → PASSIVE_SUGGEST
            low conf / not a reference                           → DISCARD
        """
        if not is_ref or confidence < self._cfg.conf_medium:
            return WatcherStatus.DISCARD

        conflicting = self._fastpath_conflict(role, ref, now)

        if confidence >= self._cfg.conf_high and ref and not conflicting:
            return WatcherStatus.AUTO_SUGGEST
        # High confidence but no usable ref, or a fast-path conflict, or only
        # medium confidence → passive.
        return WatcherStatus.PASSIVE_SUGGEST

    def _fastpath_conflict(self, role: str, ref: Optional[str], now: float) -> bool:
        with self._lock:
            st = self._streams.get(role)
            if st is None or not st.fastpath_ref:
                return False
            if (now - st.fastpath_ts) >= self._cfg.fastpath_conflict_sec:
                return False
            # A conflict is a *different* recent fast-path ref. A matching ref is
            # corroboration, not a conflict.
            return bool(ref) and st.fastpath_ref != ref

    def _dedup_ok(self, role: str, ref: str, confidence: float, now: float) -> bool:
        """True if this ref should be emitted: suppress a repeat within the
        cooldown window UNLESS confidence rose meaningfully. A changed ref is
        always allowed."""
        with self._lock:
            st = self._streams.get(role)
            if st is None:
                return True
            for (r, ts, c) in reversed(st.recent):
                if r == ref and (now - ts) < self._cfg.dedup_cooldown_sec:
                    return confidence >= (c + self._cfg.conf_rise_delta)
        return True

    def _record_emitted(self, role: str, ref: str, confidence: float, now: float) -> None:
        with self._lock:
            st = self._streams.get(role)
            if st is not None:
                st.recent.append((ref, now, confidence))

    # ── Internal: delivery ────────────────────────────────────────────────────

    def _emit(self, result: WatcherSuggestion) -> None:
        self._log.info(
            f"🔭 watcher {result.status.value.upper()} [{result.stream}/{result.language}] "
            f"{result.suggested_reference or '(no ref)'} "
            f"conf={result.confidence:.2f} ({result.explicit_or_implied}) "
            f"— {result.reasoning[:80]}"
        )
        if self._on_suggestion is None:
            return
        try:
            self._on_suggestion(result)
        except Exception as e:
            # A misbehaving callback must not break the watcher.
            self._log.debug(f"🔭 watcher on_suggestion callback error: {e}")


# ── Internal snapshot passed to the executor thread (immutable view) ──────────

@dataclass
class _Snapshot:
    role:        str
    language:    str
    window_text: str
