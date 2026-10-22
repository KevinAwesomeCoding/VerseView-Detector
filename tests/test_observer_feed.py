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
        return json.loads((Path(self.directory.name) / f"engine-{os.getpid()}.json").read_text(encoding='utf-8'))

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

    def test_connection_activity_is_typed_bounded_private_and_reset_on_start(self):
        for _ in range(20):
            self.publisher.emit('remote_connection', status='retrying', attempt=2,
                                reason='remote', exception='PRIVATE', url='SECRET', retry_seconds=999)
        self.publisher.emit('remote_connection',status='failed',attempt=True)
        data=self.snapshot()
        self.assertEqual(len(data['connection_events']),16)
        self.assertEqual(data['remote_connection']['retry_seconds'],5)
        self.assertNotIn('PRIVATE',json.dumps(data));self.assertNotIn('SECRET',json.dumps(data))
        self.publisher.begin(CONFIG)
        self.assertIsNone(self.snapshot()['remote_connection'])

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

class TranscriptHistoryTests(unittest.TestCase):
    def test_private_history_keeps_beginning_across_snapshot_limit_and_sessions(self):
        with tempfile.TemporaryDirectory() as directory:
            p=observer_feed.ObserverPublisher(True,directory)
            try:
                p.begin(CONFIG);first=p.snapshot()['session_id']
                ids=[p.emit('transcript',stream='primary' if i%2==0 else 'secondary',text=f'Final {i}',is_final=True) for i in range(120)]
                p.emit('transcript',stream='primary',text='unfinished',is_final=False)
                p.emit('translation',transcript_id=ids[-1],translation='Translated final')
                p.flush()
                rows=[json.loads(s) for s in (Path(directory)/f'transcript-{first}.jsonl').read_text().splitlines()]
                finals=[r for r in rows if not r.get('update')]
                self.assertEqual(len(finals),120)
                self.assertEqual(finals[0]['text'],'Final 0');self.assertEqual(finals[-1]['text'],'Final 119')
                self.assertEqual(len(p.snapshot()['transcripts']),48)
                self.assertEqual(rows[-1]['translation'],'Translated final')
                self.assertNotIn('unfinished',str(rows))
                if os.name!='nt':self.assertEqual((Path(directory)/f'transcript-{first}.jsonl').stat().st_mode&0o777,0o600)
                p.begin(CONFIG);second=p.snapshot()['session_id'];p.emit('transcript',stream='primary',text='New session',is_final=True);p.flush()
                self.assertNotEqual(first,second)
                self.assertNotIn('Final 0',(Path(directory)/f'transcript-{second}.jsonl').read_text())
            finally:p.close()

    def test_long_final_retains_more_than_the_snapshot_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            p=observer_feed.ObserverPublisher(True,directory)
            try:
                p.begin(CONFIG);p.emit('transcript',stream='primary',text='a'*6000,is_final=True);p.flush()
                sid=p.snapshot()['session_id'];row=json.loads((Path(directory)/f'transcript-{sid}.jsonl').read_text())
                self.assertEqual(len(row['text']),6000)
                self.assertEqual(len(p.snapshot()['transcripts'][0]['text']),2000)
            finally:p.close()

    def test_history_write_failure_keeps_recent_live_snapshot_available(self):
        with tempfile.TemporaryDirectory() as directory:
            p=observer_feed.ObserverPublisher(True,directory)
            try:
                p.begin(CONFIG);p._stop.set();p._wake.set();p._thread.join(timeout=2)
                p.emit('transcript',stream='primary',text='Still visible',is_final=True)
                with patch('observer_feed.os.open',side_effect=OSError('history unavailable')):
                    # Isolate the history opener; NamedTemporaryFile uses its own
                    # opener too, so verify live snapshot in the next successful flush.
                    try:p.flush()
                    except OSError:pass
                p.flush();snapshot=p.snapshot()
                self.assertEqual(snapshot['transcripts'][-1]['text'],'Still visible')
                self.assertFalse(snapshot['history_available'])
            finally:p.close()
