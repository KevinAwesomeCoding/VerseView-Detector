import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from desktop_suggestions import WatcherInbox


class SuggestionTests(unittest.TestCase):
    def setUp(self):
        self.now = 100
        self.running = True
        self.engine = SimpleNamespace(_controller=object(),
            _normalize_delivery_reference=lambda ref: ref if isinstance(ref,str) and ref.startswith('John 3:') else None,
            _reject_verse_out_of_range=lambda ref: False, get_watcher_status=lambda:dict(has_clients=True,cycles=1),
            deliver_verse=Mock(return_value=True),set_context=Mock(),add_to_verse_history=Mock())
        self.inbox = WatcherInbox(self.engine,lambda:self.running,lambda:self.now)
        self.callback = self.inbox.prepare(True)
        self.addCleanup(self.inbox.join)

    def suggestion(self, ref='John 3:19', stream='secondary', kind='passive_suggest'):
        return SimpleNamespace(suggested_reference=ref,status=SimpleNamespace(value=kind),stream=stream,
            language='ml',confidence=.7,reasoning='A paraphrase of this passage.',raw={'key':'SECRET'},window_text='PRIVATE-WINDOW')

    def test_bounded_projection_omits_provider_payload_and_never_delivers(self):
        for number in range(10): self.callback(self.suggestion('John 3:'+str(number+10)))
        rows=self.inbox.snapshot()['rows']
        self.assertEqual(len(rows),6)
        self.assertEqual(rows[0]['reference'],'John 3:14')
        self.assertNotIn('PRIVATE',str(rows));self.assertNotIn('SECRET',str(rows))
        self.engine.deliver_verse.assert_not_called()
        self.callback(self.suggestion(kind='auto_suggest'))
        self.assertEqual(self.inbox.snapshot()['rows'][-1]['state'],'available')
        self.engine.deliver_verse.assert_not_called()

    def test_refresh_expiry_old_session_and_stop_invalidate_actions(self):
        self.callback(self.suggestion()); old=self.inbox.snapshot()['rows'][0]['id']
        self.callback(self.suggestion()); new=self.inbox.snapshot()['rows'][0]['id']
        self.assertNotEqual(old,new)
        with self.assertRaises(ValueError): self.inbox.send(old)
        self.now+=91
        with self.assertRaises(ValueError): self.inbox.send(new)
        self.assertEqual(self.inbox.snapshot()['rows'],[])
        new_callback=self.inbox.prepare(True)
        self.callback(self.suggestion());self.assertEqual(self.inbox.snapshot()['rows'],[])
        new_callback(self.suggestion());current=self.inbox.snapshot()['rows'][0]['id']
        self.running=False
        with self.assertRaises(ValueError): self.inbox.send(current)
        self.inbox.cancel();new_callback(self.suggestion('John 3:20'))
        self.assertEqual(len(self.inbox.snapshot()['rows']),1)
        self.engine.deliver_verse.assert_not_called()

    def test_preview_dismiss_clear_and_mode_change_invalidate_advice_without_delivery(self):
        self.callback(self.suggestion(kind='auto_suggest'))
        row=self.inbox.snapshot()['rows'][0];revision=self.inbox.snapshot()['revision']
        self.assertEqual(self.inbox.select(row['id'])['reference'],'John 3:19')
        self.callback(self.suggestion('John 3:20'))
        with self.assertRaises(ValueError):self.inbox.clear(revision)
        self.inbox.dismiss(row['id'])
        with self.assertRaises(ValueError):self.inbox.select(row['id'])
        self.inbox.clear(self.inbox.snapshot()['revision']);self.assertEqual(self.inbox.snapshot()['rows'],[])
        self.engine.get_watcher_status=lambda:dict(has_clients=True,cycle_state='suggested')
        self.assertEqual(self.inbox.snapshot()['phase'],'waiting')
        self.callback(self.suggestion());identity=self.inbox.snapshot()['rows'][0]['id']
        self.engine._delivery_epoch=1
        self.assertEqual(self.inbox.snapshot()['rows'],[])
        with self.assertRaises(ValueError):self.inbox.send(identity)
        self.engine.deliver_verse.assert_not_called()

    def test_status_only_reports_evidenced_states_without_private_provider_details(self):
        status={'has_clients':True,'cycle_state':'waiting','effective_route':'free-profile','private':'SECRET'}
        self.engine.get_watcher_status=lambda:status
        self.assertEqual(self.inbox.snapshot()['phase'],'waiting')
        for phase in ('failed','rate_limited','budget_limited','configuration_required'):
            status['cycle_state']=phase;self.assertEqual(self.inbox.snapshot()['phase'],phase)
        status['scanning']=True;self.assertEqual(self.inbox.snapshot()['phase'],'scanning')
        self.assertNotIn('SECRET',str(self.inbox.snapshot()))
        self.inbox.cancel();self.assertEqual(self.inbox.snapshot()['phase'],'stopped')

    def test_manual_send_uses_guarded_path_with_candidate_and_actual_acceptance(self):
        self.callback(self.suggestion());identity=self.inbox.snapshot()['rows'][0]['id']
        self.inbox.send(identity);self.inbox.join()
        row=self.inbox.snapshot()['rows'][0]
        self.assertEqual(row['state'],'accepted')
        self.engine.deliver_verse.assert_called_once_with('John 3:19',self.engine._controller,bypass_cooldown=False,
            confidence=1.0,source='WATCHER-MANUAL',stream='secondary',candidate_id=row['candidate_id'],expected_epoch=0)
        self.engine.set_context.assert_called_once_with('John','3','19')
        with self.assertRaises(ValueError):self.inbox.send(identity)

    def test_no_acceptance_does_not_update_context_or_automatically_retry(self):
        self.engine.deliver_verse.return_value=False
        self.callback(self.suggestion());identity=self.inbox.snapshot()['rows'][0]['id']
        self.inbox.send(identity);self.inbox.join()
        self.assertEqual(self.inbox.snapshot()['rows'][0]['state'],'review')
        self.engine.set_context.assert_not_called();self.engine.add_to_verse_history.assert_not_called()
        with self.assertRaises(ValueError):self.inbox.send(identity)
        self.engine.deliver_verse.assert_called_once()

    def test_post_acceptance_error_cannot_erase_acceptance(self):
        self.engine.set_context.side_effect=ValueError('PRIVATE-ERROR')
        self.callback(self.suggestion());identity=self.inbox.snapshot()['rows'][0]['id']
        with patch('desktop_suggestions.logging.getLogger'):
            self.inbox.send(identity);self.inbox.join()
        self.assertEqual(self.inbox.snapshot()['rows'][0]['state'],'accepted')
        self.assertNotIn('PRIVATE',str(self.inbox.snapshot()))

    def test_stop_retains_unknown_inflight_outcome_and_owned_worker(self):
        entered,release=threading.Event(),threading.Event()
        def blocked(*_args,**_kwargs):
            entered.set();release.wait(3);return True
        self.engine.deliver_verse.side_effect=blocked
        self.callback(self.suggestion());identity=self.inbox.snapshot()['rows'][0]['id']
        try:
            self.inbox.send(identity);self.assertTrue(entered.wait(2))
            self.assertTrue(self.inbox.snapshot()['busy'])
            self.inbox.cancel()
            self.assertEqual(self.inbox.snapshot()['rows'][0]['state'],'unknown')
            with self.assertRaises(ValueError):self.inbox.send(identity)
            release.set();self.inbox.join()
            self.assertEqual(self.inbox.snapshot()['rows'][0]['state'],'unknown')
            self.engine.set_context.assert_not_called()
        finally: release.set();self.inbox.join()


if __name__=='__main__':unittest.main()
