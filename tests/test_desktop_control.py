import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock
import uuid

from desktop_control import DesktopControl
from observer_feed import ObserverPublisher


class DesktopControlTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.publisher = ObserverPublisher(True, self.temporary.name)
        self.publisher.begin({'streams': {}})
        self.addCleanup(self.publisher.close)
        self.state = 'stopped'
        self.start, self.stop = Mock(return_value=True), Mock()
        self.broker = DesktopControl(self.publisher, lambda: self.state, self.start, self.stop,
                                     enabled=True, clock=lambda: 1000)
        self.addCleanup(self.broker.close)

    def request(self, action='start', **updates):
        return dict(id=uuid.uuid4().hex, control_id=self.broker.control_id,
                    session_id=self.publisher.snapshot()['session_id'], created_at=1000,
                    action=action, **updates)

    def result(self):
        return self.publisher.snapshot()['control']['results'][-1]

    def hold(self, candidate='candidate-1'):
        self.state = 'running'
        answer = []
        thread = threading.Thread(target=lambda: answer.append(
            self.broker.confirm('John 3:18', .3, candidate, 'TEST', 'secondary')))
        thread.start()
        self.addCleanup(thread.join, 1)
        self.addCleanup(self.broker.close)
        deadline = time.monotonic() + 2
        while candidate not in self.broker.pending and time.monotonic() < deadline:
            time.sleep(.005)
        self.assertIn(candidate, self.broker.pending)
        return thread, answer

    def test_start_queued_before_emergency_cannot_restart_after_save_finishes(self):
        operator = Mock()
        operator.start_after = 1000
        operator.snapshot.return_value = {'busy': False, 'emergency': True}
        self.broker.operator = operator
        self.broker.execute(self.request())
        self.start.assert_not_called()
        self.assertEqual(self.result()['outcome'], 'rejected')
        operator.start_after = 999
        self.broker.execute(self.request())
        self.start.assert_called_once()

    def test_start_once_and_scheduling_ack(self):
        request = self.request()
        self.broker.execute(request)
        self.broker.execute(request)
        self.start.assert_called_once()
        self.assertEqual(self.result()['outcome'], 'requested')
        self.assertEqual(self.publisher.snapshot()['control']['state'], 'stopped')

    def test_ask_before_sending_switch_persists_and_cancels_pending(self):
        engine = Mock(ASK_BEFORE_SENDING=False)
        preference = Path(self.temporary.name) / 'approval-preferences.json'
        self.broker.close()
        self.broker = DesktopControl(self.publisher, lambda: self.state, self.start, self.stop,
                                     enabled=True, clock=lambda: 1000, engine=engine, preference_path=preference)
        self.broker.execute(self.request('set_ask_before_sending', enabled=True))
        self.assertEqual(self.result()['outcome'], 'saved')
        self.assertTrue(engine.ASK_BEFORE_SENDING)
        self.assertTrue(json.loads(preference.read_text())['ask_before_sending'])
        thread, answer = self.hold()
        self.broker.execute(self.request('set_ask_before_sending', enabled=False))
        thread.join(1)
        self.assertEqual(answer, [False])
        self.assertFalse(engine.ASK_BEFORE_SENDING)

    def test_display_suppressed_requires_matching_detected_event(self):
        self.state='running'
        verses=Mock()
        verses.snapshot.return_value={'send_busy':False,'lookup_busy':False}
        self.broker.verses=verses
        self.publisher.emit('delivery', event={'candidate_id':'a'*12,'reference':'John 10:12','outcome':'SUPPRESSED'})
        self.broker.refresh()
        self.broker.execute(self.request('display_suppressed',candidate_id='a'*12,reference='John 10:12'))
        self.assertEqual(self.result()['outcome'],'requested')
        verses.display_suppressed.assert_called_once_with('a'*12,'John 10:12')
        self.broker.execute(self.request('display_suppressed',candidate_id='a'*12,reference='John 10:11'))
        self.assertEqual(self.result()['outcome'],'rejected')

    def test_pending_review_contains_bounded_spoken_context(self):
        self.publisher.emit('transcript', stream='secondary', text='Earlier sentence.', is_final=True)
        self.publisher.emit('transcript', stream='secondary', text='Please read John 3:18 now.', is_final=True)
        self.publisher.flush()
        thread, _ = self.hold()
        context = self.publisher.snapshot()['control']['pending'][0]['context']
        self.assertEqual(context['before'], 'Earlier sentence.')
        self.assertEqual(context['detected'], 'Please read John 3:18 now.')
        self.broker.execute(self.request('reject', candidate_id='candidate-1'))
        thread.join(1)

    def test_rejects_wrong_session_control_expired_future_and_unknown_action(self):
        for key, value in [('session_id', 'a'*32), ('control_id', 'b'*32),
                           ('created_at', 989), ('created_at', 1001), ('action', 'goto')]:
            request = self.request()
            request[key] = value
            self.broker.execute(request)
            self.assertEqual(self.result()['outcome'], 'rejected')
        self.start.assert_not_called()

    def test_checks_state_when_executed(self):
        self.state = 'starting'
        self.broker.execute(self.request('stop'))
        self.broker.execute(self.request('start'))
        self.start.assert_not_called()
        self.stop.assert_not_called()

    def test_start_failure_is_not_reported_running(self):
        self.start.return_value = False
        self.broker.execute(self.request())
        self.assertEqual(self.result()['outcome'], 'failed')
        self.assertEqual(self.publisher.snapshot()['control']['state'], 'stopped')

    def test_new_session_is_available_only_stopped_and_delegates_to_notes(self):
        notes = Mock()
        notes.snapshot.return_value = {'busy': False, 'pending_auto': False}
        self.broker.notes = notes
        self.broker.refresh()
        self.assertIn('new_session', self.publisher.snapshot()['control']['actions'])
        self.broker.execute(self.request('new_session'))
        notes.new_session.assert_called_once()
        self.assertEqual(self.result()['action'], 'new_session')
        self.state = 'running'
        self.broker.execute(self.request('new_session'))
        notes.new_session.assert_called_once()
        self.assertEqual(self.result()['outcome'], 'rejected')

    def test_approval_targets_exact_candidate_and_cannot_repeat(self):
        thread, answer = self.hold()
        self.broker.execute(self.request('approve', candidate_id='different'))
        self.assertEqual(self.result()['outcome'], 'rejected')
        request = self.request('approve', candidate_id='candidate-1')
        self.broker.execute(request)
        thread.join(2)
        self.assertEqual(answer, [True])
        self.broker.execute(self.request('approve', candidate_id='candidate-1'))
        self.assertEqual(self.result()['outcome'], 'rejected')

    def test_reject_and_stop_release_waiters_without_approval(self):
        thread, answer = self.hold()
        self.broker.execute(self.request('reject', candidate_id='candidate-1'))
        thread.join(2)
        self.assertEqual(answer, [False])
        thread, answer = self.hold('candidate-2')
        self.broker.execute(self.request('stop'))
        thread.join(2)
        self.assertEqual(answer, [False])
        self.stop.assert_called_once()

    def test_session_restart_cancels_pending_and_rejects_old_commands(self):
        thread, answer = self.hold()
        request = self.request('approve', candidate_id='candidate-1')
        self.publisher.begin({'streams': {}})
        self.broker.execute(request)
        thread.join(2)
        self.assertEqual(answer, [False])
        self.assertEqual(self.result()['outcome'], 'rejected')

    def test_inbox_is_atomic_bounded_and_bad_json_does_not_break_tick(self):
        request = self.request()
        file = self.broker.directory / f"command-{request['id']}.json"
        file.write_text(json.dumps(request))
        bad = self.broker.directory / f"command-{'a'*32}.json"
        bad.write_text('{bad')
        self.broker.tick()
        self.start.assert_called_once()
        self.assertFalse(file.exists())
        self.assertFalse(bad.exists())
        self.assertEqual(self.result()['id'], request['id'])

    def test_command_age_does_not_expire_or_approve_a_held_candidate(self):
        thread, answer = self.hold()
        self.broker.clock = lambda: 999999
        thread.join(.15)
        self.assertTrue(thread.is_alive())
        self.assertEqual(answer, [])
        self.broker.close()
        thread.join(1)
        self.assertEqual(answer, [False])

    def test_close_disables_controls_and_removes_own_inbox(self):
        thread, answer = self.hold()
        self.broker.close()
        thread.join(2)
        self.assertEqual(answer, [False])
        self.assertFalse(self.broker.directory.exists())
        self.assertEqual(self.publisher.snapshot()['control']['actions'], [])

    def test_managed_clear_delegates_to_existing_panic_action(self):
        self.state = 'running'
        self.broker.panic = Mock()
        self.broker.execute(self.request('panic'))
        self.broker.panic.assert_called_once()
        self.assertEqual(self.result()['outcome'], 'requested')
        self.start.assert_not_called()

    def test_suggestion_sends_are_running_session_bound_and_never_acknowledge_acceptance(self):
        suggestions=Mock()
        suggestions.snapshot.return_value=dict(active=True,busy=False,rows=[])
        self.broker.suggestions=suggestions
        identity='d'*32
        self.broker.execute(self.request('send_suggestion',suggestion_id=identity))
        suggestions.send.assert_not_called()
        self.state='running'
        self.broker.execute(self.request('send_suggestion',suggestion_id='../../settings.json'))
        suggestions.send.assert_not_called()
        self.broker.execute(self.request('send_suggestion',suggestion_id=identity,reference='John 3:16'))
        suggestions.send.assert_not_called()
        request=self.request('send_suggestion',suggestion_id=identity)
        self.broker.execute(request);self.broker.execute(request)
        suggestions.send.assert_called_once_with(identity)
        self.assertEqual(self.result()['outcome'],'requested')
        self.assertIn('inspect delivery activity',self.result()['reason'])

    def test_outline_edits_check_revision_state_and_do_not_start_or_present(self):
        from desktop_outline import SessionOutline
        outline=SessionOutline();self.broker.outline=outline
        revision=outline.snapshot()['revision']
        self.broker.execute(self.request('edit_outline',outline_revision=revision,outline_text='കുറിപ്പുകൾ'))
        self.assertEqual(self.result()['outcome'],'saved')
        self.assertEqual(outline.snapshot()['text'],'കുറിപ്പുകൾ')
        self.start.assert_not_called();self.stop.assert_not_called()
        self.broker.execute(self.request('edit_outline',outline_revision=revision,outline_text='Stale replacement'))
        self.assertEqual(self.result()['outcome'],'rejected')
        self.assertEqual(outline.snapshot()['text'],'കുറിപ്പുകൾ')
        self.state='stopping'
        self.broker.execute(self.request('edit_outline',outline_revision=outline.snapshot()['revision'],outline_text='During stop'))
        self.assertEqual(self.result()['outcome'],'rejected')

    def test_recovery_decisions_require_current_revision_and_stopped_host(self):
        from desktop_recovery import SessionRecovery
        recovery = SessionRecovery(self.temporary.name)
        recovery.save({'transcript': 'Saved sermon'}, 'autosave')
        self.broker.recovery = SessionRecovery(self.temporary.name)
        self.broker.refresh()
        revision = self.publisher.snapshot()['control']['recovery']['revision']
        self.broker.execute(self.request('start'))
        self.start.assert_not_called()
        self.broker.execute(self.request('restore_session', recovery_revision='f'*32))
        self.assertEqual(self.result()['outcome'], 'rejected')
        self.broker.execute(self.request('restore_session', recovery_revision=revision))
        self.assertEqual(self.result()['outcome'], 'prepared')
        self.assertEqual(self.publisher.snapshot()['control']['state'], 'stopped')
        self.start.assert_not_called()
        self.broker.execute(self.request('restore_session', recovery_revision=revision))
        self.assertEqual(self.result()['outcome'], 'rejected')
        self.state = 'running'
        self.broker.execute(self.request('discard_session', recovery_revision=revision))
        self.assertEqual(self.result()['outcome'], 'rejected')
        self.assertTrue(recovery.path.exists())
        self.state = 'stopped'
        self.broker.execute(self.request('discard_session', recovery_revision=revision))
        self.assertEqual(self.result()['outcome'], 'discarded')
        self.assertFalse(recovery.path.exists())
        self.start.assert_not_called()

    def test_no_side_effects_without_explicit_opt_in(self):
        disabled = DesktopControl(self.publisher, lambda: 'stopped', self.start, self.stop)
        disabled.tick()
        self.assertFalse(disabled.directory.exists())
        self.assertEqual(list(Path(self.temporary.name).glob('control-*')), [self.broker.directory])


if __name__ == '__main__':
    unittest.main()
