"""Opt-in, dashboard telemetry. No sockets or new dependencies.

Set VERSEVIEW_OBSERVER=1 before starting the detector. A background writer emits
bounded atomic snapshots in the user's VerseView/Observer directory. Observation
must never change detection decisions or raise into a provider callback.
"""
import atexit
import copy
import datetime as dt
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import uuid


def observer_directory(platform=None, home=None, appdata=None):
    platform = platform or sys.platform
    home = Path(home or Path.home())
    if platform == "darwin":
        return home / "Library" / "Application Support" / "VerseView" / "Observer"
    if platform == "win32":
        return Path(appdata or os.getenv("APPDATA", str(home))) / "VerseView" / "Observer"
    return home / ".verseview" / "Observer"


def _text(value, limit=2000):
    return value[:limit] if isinstance(value, str) else ""


def _now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


class ObserverPublisher:
    def __init__(self, enabled=False, directory=None):
        self.enabled = enabled
        self.directory = Path(directory) if directory else observer_directory()
        self._lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread = None
        self._data = None

    def begin(self, config, origin="engine"):
        if not self.enabled:
            return
        with self._lock:
            streams = {}
            for role in ("primary", "secondary"):
                value = config.get("streams", {}).get(role, {})
                streams[role] = {"language": _text(value.get("language"), 24),
                                 "provider": _text(value.get("provider"), 64),
                                 "enabled": bool(value.get("enabled"))}
            self._data = {"schema": 1, "session_id": uuid.uuid4().hex,
                          "pid": os.getpid(), "origin": "callback-replay" if origin == "callback-replay" else "engine",
                          "started_at": _now(), "updated_at": _now(), "revision": 0,
                          "engine_state": "configured", "config": {"streams": streams,
                          "bible_translation": _text(config.get("bible_translation"), 64)},
                          "streams": {role: {"state": "configured" if streams[role]["enabled"] else "disabled",
                                             "last_transcript_at": None} for role in streams},
                          "transcripts": [], "delivery_events": []}
        if self._thread is None or not self._thread.is_alive():
            self._stop.clear()
            self._thread = threading.Thread(target=self._run, name="VerseViewObserver", daemon=True)
            self._thread.start()
        self._wake.set()

    def emit(self, kind, **values):
        if not self.enabled:
            return
        result = None
        with self._lock:
            if self._data is None:
                return
            data = self._data
            role = values.get("stream")
            if kind == "transcript" and role in ("primary", "secondary"):
                stream = data["config"]["streams"][role]
                row = {"id": uuid.uuid4().hex, "stream": role, "timestamp": _now(),
                       "language": stream["language"], "provider": stream["provider"],
                       "text": _text(values.get("text")), "translation": _text(values.get("translation")),
                       "is_final": bool(values.get("is_final"))}
                if not row["text"]:
                    return
                # One replaceable partial per stream; finals are retained independently.
                data["transcripts"] = [item for item in data["transcripts"]
                                       if item["is_final"] or item["stream"] != role]
                data["transcripts"].append(row)
                data["transcripts"] = data["transcripts"][-48:]
                data["streams"][role] = {"state": "transcript_received", "last_transcript_at": row["timestamp"]}
                result = row["id"]
            elif kind == "translation":
                row = next((item for item in data["transcripts"] if item["id"] == values.get("transcript_id")), None)
                if row is None:
                    return
                row["translation"] = _text(values.get("translation"))
            elif kind == "delivery":
                event = values.get("event", {})
                # Do not export arbitrary context, credentials, provider metadata or exceptions.
                limits = {"candidate_id": 128, "reference": 128, "source": 64, "stream": 24,
                          "language": 24, "timestamp": 64, "stage": 64, "outcome": 64, "reason": 400}
                row = {key: _text(event.get(key), limit) for key, limit in limits.items()}
                if row["stream"] not in ("primary", "secondary"):
                    row["stream"] = "unknown"
                data["delivery_events"].append(row)
                data["delivery_events"] = data["delivery_events"][-192:]
            elif kind == "host":
                value = values.get("value", {})
                safe = {"managed": value.get("managed") is True, "verification": value.get("verification") is True,
                        "notice": _text(value.get("notice"), 500)}
                if data.get("host") == safe:
                    return
                data["host"] = safe
            elif kind == "control":
                value = copy.deepcopy(values.get("value"))
                if data.get("control") == value:
                    return
                data["control"] = value
            elif kind == "state":
                data["engine_state"] = _text(values.get("state"), 64)
            elif kind == "stream" and role in data["streams"]:
                data["streams"][role]["state"] = _text(values.get("state"), 64)
            else:
                return
            data["revision"] += 1
        self._wake.set()
        return result

    def snapshot(self):
        with self._lock:
            return copy.deepcopy(self._data)

    def flush(self):
        """Atomic write, also usable by isolated integration tests."""
        with self._write_lock:
            with self._lock:
                if not self._data:
                    return
                data = copy.deepcopy(self._data)
            data["updated_at"] = _now()
            self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            destination = self.directory / f"engine-{os.getpid()}.json"
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.directory,
                                                 prefix=".snapshot-", delete=False) as handle:
                    temporary = handle.name
                    json.dump(data, handle, ensure_ascii=False)
                os.replace(temporary, destination)
            finally:
                if temporary and os.path.exists(temporary):
                    os.unlink(temporary)

    def _run(self):
        while not self._stop.is_set():
            self._wake.wait(1)
            self._wake.clear()
            try:
                self.flush()
            except Exception:
                # Read-only diagnostics must not disrupt the speech/delivery engine.
                pass
            # Coalesce bursts instead of writing once per provider partial/event.
            self._stop.wait(.2)

    def close(self):
        if self.enabled and self._data:
            self.emit("state", state="stopped")
            self._stop.set()
            self._wake.set()
            if self._thread:
                self._thread.join(timeout=1)
            try:
                self.flush()
            except Exception:
                pass


_publisher = ObserverPublisher(enabled=os.getenv("VERSEVIEW_OBSERVER") == "1",
                               directory=os.getenv("VERSEVIEW_OBSERVER_DIRECTORY"))
atexit.register(_publisher.close)


def begin(config, origin="engine"):
    try:
        _publisher.begin(config, origin)
    except Exception:
        pass


def emit(kind, **values):
    try:
        return _publisher.emit(kind, **values)
    except Exception:
        pass
