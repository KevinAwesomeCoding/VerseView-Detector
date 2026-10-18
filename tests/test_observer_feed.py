"""Isolated observer export tests; no microphone, provider, or presentation calls."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import observer_feed


CONFIG = {"streams": {"primary": {"language": "en", "provider": "deepgram", "enabled": True},
                      "secondary": {"language": "ml", "provider": "sarvam", "enabled": True}},
          "bible_translation": "KJV", "api_key": "must-not-export"}


class ObserverTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.publisher = observer_feed.ObserverPublisher(True, self.directory.name)
        self.publisher.begin(CONFIG, origin="callback-replay")

    def tearDown(self):
        self.publisher.close()
        self.directory.cleanup()

    def snapshot(self):
        self.publisher.flush()
        return json.loads((Path(self.directory.name) / f"engine-{os.getpid()}.json").read_text())

    def test_disabled_export_does_not_create_files_or_threads(self):
        disabled = observer_feed.ObserverPublisher(False, Path(self.directory.name) / "disabled")
        disabled.begin(CONFIG)
        disabled.emit("transcript", stream="primary", text="John 3:16", is_final=True)
        self.assertIsNone(disabled._thread)
        self.assertFalse(disabled.directory.exists())

    def test_raw_and_translation_keep_explicit_stream_and_language(self):
        self.publisher.emit("transcript", stream="secondary", text="യോഹന്നാൻ 3:16",
                            translation="John 3:16", is_final=True, api_key="secret")
        row = self.snapshot()["transcripts"][0]
        self.assertEqual((row["stream"], row["language"], row["provider"]), ("secondary", "ml", "sarvam"))
        self.assertEqual(row["text"], "യോഹന്നാൻ 3:16")
        self.assertEqual(row["translation"], "John 3:16")
        self.assertNotIn("secret", json.dumps(self.snapshot()))

    def test_partial_replacement_is_per_stream_and_finals_are_retained(self):
        for role, final in (("primary", True), ("secondary", False), ("primary", False), ("primary", False)):
            self.publisher.emit("transcript", stream=role, text="speech", is_final=final)
        rows = self.snapshot()["transcripts"]
        self.assertEqual(len(rows), 3)
        self.assertEqual(len([row for row in rows if row["stream"] == "primary" and row["is_final"]]), 1)
        self.publisher.emit("transcript", stream="secondary", text="final", is_final=True)
        self.assertFalse(any(row["stream"] == "secondary" and not row["is_final"] for row in self.snapshot()["transcripts"]))

    def test_translation_updates_its_raw_transcript_by_identity(self):
        transcript_id = self.publisher.emit("transcript", stream="secondary", text="യോഹന്നാൻ 3:16", is_final=True)
        self.publisher.emit("transcript", stream="primary", text="another line", is_final=True)
        self.publisher.emit("translation", transcript_id=transcript_id, translation="John 3:16")
        rows = self.snapshot()["transcripts"]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["translation"], "John 3:16")
        self.assertEqual(rows[0]["id"], transcript_id)
        self.assertEqual(rows[1]["translation"], "")

    def test_events_are_bounded_and_context_secrets_are_excluded(self):
        for index in range(220):
            self.publisher.emit("delivery", event={"candidate_id": str(index), "reference": "John 3:16",
                "stream": None, "outcome": "SUPPRESSED", "api_key": "secret", "exception": "sensitive"})
        data = self.snapshot()
        self.assertEqual(len(data["delivery_events"]), 192)
        self.assertEqual(data["delivery_events"][-1]["stream"], "unknown")
        self.assertNotIn("secret", json.dumps(data))
        self.assertNotIn("sensitive", json.dumps(data))
        self.assertNotIn("must-not-export", json.dumps(data))

    def test_new_session_resets_old_transcripts_and_events(self):
        old = self.snapshot()["session_id"]
        self.publisher.emit("transcript", stream="primary", text="old", is_final=True)
        self.publisher.begin(CONFIG)
        data = self.snapshot()
        self.assertNotEqual(old, data["session_id"])
        self.assertEqual(data["transcripts"], [])
        self.assertEqual(data["origin"], "engine")

    def test_snapshot_is_atomic_private_and_stops_cleanly(self):
        self.publisher.close()
        data = self.snapshot()
        self.assertEqual(data["engine_state"], "stopped")
        self.assertFalse(self.publisher._thread.is_alive())
        self.assertEqual(len(list(Path(self.directory.name).glob('.snapshot-*'))), 0)
        if os.name != 'nt':
            self.assertEqual((Path(self.directory.name) / f"engine-{os.getpid()}.json").stat().st_mode & 0o777, 0o600)

    def test_export_failure_does_not_escape_into_engine_calls(self):
        with patch.object(observer_feed, '_publisher') as publisher:
            publisher.emit.side_effect = OSError('disk unavailable')
            publisher.begin.side_effect = OSError('disk unavailable')
            observer_feed.emit('transcript', stream='primary', text='speech')
            observer_feed.begin(CONFIG)

    def test_platform_directories_match_the_existing_detector_profile(self):
        self.assertEqual(observer_feed.observer_directory('darwin', '/home/test'), Path('/home/test/Library/Application Support/VerseView/Observer'))
        self.assertEqual(observer_feed.observer_directory('win32', '/home/test', '/roaming'), Path('/roaming/VerseView/Observer'))


if __name__ == '__main__':
    unittest.main()
