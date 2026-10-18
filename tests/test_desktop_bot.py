import asyncio
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import urllib.error
import urllib.request
import uuid

from desktop_bot import DesktopBot, BotError
from desktop_bot_bridge import ManagedBotBridge, current_reference, stepped_reference
from desktop_bot_process import owned_lifetime, bridge_request
from observer_feed import ObserverPublisher
from desktop_control import DesktopControl
import vv_streaming_master as engine


class BotTests(unittest.TestCase):
    def runtime(self,path):
        return SimpleNamespace(profile=path,verification=True,state=lambda:'running',stop_requested=threading.Event(),
                               publisher=ObserverPublisher(True,path),engine=engine)

    def test_navigation_uses_known_canonical_bounds_and_never_guesses_context(self):
        with patch.multiple(engine,current_book='John',current_chapter='3',current_verse='36'):
            self.assertEqual(stepped_reference(engine,1),'John 4:1')
            engine.current_chapter='4';engine.current_verse='1'
            self.assertEqual(stepped_reference(engine,-1),'John 3:36')
            engine.current_book='Psalm';engine.current_chapter='1';engine.current_verse='6'
            self.assertEqual(stepped_reference(engine,1),'Psalm 2:1')
            engine.current_book='Genesis';engine.current_chapter='1';engine.current_verse='1'
            self.assertIsNone(stepped_reference(engine,-1))
            engine.current_book='Revelation';engine.current_chapter='22';engine.current_verse='21'
            self.assertIsNone(stepped_reference(engine,1))
            engine.current_chapter='23';self.assertIsNone(current_reference(engine))
            engine.current_book=None;self.assertIsNone(stepped_reference(engine,1))

    def test_private_auth_expiry_replay_and_bounded_sanitized_events(self):
        bridge=ManagedBotBridge(SimpleNamespace(),clock=lambda:100)
        headers={'X-VerseView-Token':bridge.token,'X-VerseView-Request':uuid.uuid4().hex,'X-VerseView-Created':'100'}
        self.assertEqual(bridge.authenticate(headers),headers['X-VerseView-Request'])
        self.assertIsNone(bridge.authenticate(headers))
        for created in ('89','101','nan','inf'):
            self.assertIsNone(bridge.authenticate({**headers,'X-VerseView-Created':created,'X-VerseView-Request':uuid.uuid4().hex}))
        self.assertIsNone(bridge.authenticate({**headers,'X-VerseView-Token':'incorrect'}))
        for _ in range(40):bridge.record(uuid.uuid4().hex,'/goto',409)
        self.assertEqual(len(bridge.snapshot()),32);self.assertNotIn(bridge.token,str(bridge.snapshot()))

    def test_manual_command_keeps_delivery_checks_and_acceptance_identity(self):
        bridge=ManagedBotBridge(SimpleNamespace(engine=engine,stop_requested=threading.Event()))
        identity=uuid.uuid4().hex
        with patch.object(engine,'deliver_verse',return_value=False) as deliver,patch.object(engine,'set_context') as context,patch.object(engine,'add_to_verse_history') as history:
            self.assertFalse(bridge.present('John 3:19',identity));context.assert_not_called();history.assert_not_called()
            self.assertFalse(bridge.present('John 99:1',identity));self.assertEqual(deliver.call_count,1)
            deliver.return_value=True
            self.assertTrue(bridge.present('John 3:19',identity))
            self.assertEqual(deliver.call_args.kwargs,dict(bypass_cooldown=True,confidence=1.0,source='DISCORD-MANUAL',stream='unknown',candidate_id=identity))
            context.assert_called_once_with('John','3','19')
            context.side_effect=ValueError('PRIVATE')
            with patch('desktop_bot_bridge.logging.getLogger'):self.assertTrue(bridge.present('John 3:20',identity))

    def test_http_requires_auth_and_remote_start_reuses_recovery_capabilities(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime=self.runtime(Path(directory));runtime.state=lambda:'stopped'
            runtime.publisher.begin({'streams':{}})
            start=Mock(return_value=True)
            control=DesktopControl(runtime.publisher,runtime.state,start,Mock(),enabled=True)
            bridge=ManagedBotBridge(runtime);bridge.start()
            try:
                base='http://127.0.0.1:'+str(bridge.port)
                with self.assertRaises(urllib.error.HTTPError) as rejected:urllib.request.urlopen(base+'/start')
                self.assertEqual(rejected.exception.code,403);start.assert_not_called()
                with patch.dict(os.environ,{'VV_BRIDGE_TOKEN':bridge.token}):
                    result=[];worker=threading.Thread(target=lambda:result.append(bridge_request(base,'/start')));worker.start()
                    deadline=time.monotonic()+2
                    while worker.is_alive() and time.monotonic()<deadline:control.tick();time.sleep(.01)
                    worker.join(3);self.assertEqual(result[0][0],200);start.assert_called_once()
                    # A checkpoint decision removes Start; the bridge must not bypass it.
                    control.recovery=SimpleNamespace(snapshot=lambda:dict(status='available'))
                    control.refresh()
                    self.assertEqual(bridge_request(base,'/start')[0],409)
                    self.assertEqual(bridge_request(base,'/goto',{'ref':'John 3:16'})[0],503)
            finally:bridge.stop();control.close();runtime.publisher.close()

    def test_stop_drain_retains_ownership_until_inflight_command_finishes(self):
        runtime=SimpleNamespace(state=lambda:'running',stop_requested=threading.Event())
        bridge=ManagedBotBridge(runtime);entered=threading.Event();release=threading.Event()
        def request():
            with bridge.delivery():entered.set();release.wait(2)
        worker=threading.Thread(target=request);worker.start();self.assertTrue(entered.wait(1))
        runtime.stop_requested.set();drained=threading.Event()
        waiter=threading.Thread(target=lambda:(bridge.drain(),drained.set()));waiter.start()
        try:
            self.assertFalse(drained.wait(.05))
            with self.assertRaises(ValueError):
                with bridge.delivery():pass
        finally:release.set();worker.join();waiter.join()
        self.assertTrue(drained.is_set())

    def test_owned_subprocess_is_opt_in_private_and_stops_on_close(self):
        with tempfile.TemporaryDirectory() as directory:
            profile=Path(directory)/'QA'/'Backend';profile.mkdir(parents=True)
            runtime=self.runtime(profile);runtime.state=lambda:'stopped'
            values={'discord_bot_token':'SECRET-SYNTHETIC','vv_guild_id':'123'}
            bot=DesktopBot(runtime,lambda:(values,'revision'))
            try:
                self.assertEqual(bot.snapshot()['status'],'stopped');self.assertIsNone(bot.child)
                bot.start()
                with self.assertRaises(BotError):bot.start()
                deadline=time.monotonic()+10
                while bot.snapshot()['status']=='starting' and time.monotonic()<deadline:time.sleep(.05)
                snapshot=bot.snapshot();self.assertEqual(snapshot['status'],'online',snapshot)
                self.assertFalse(snapshot['proof']['guiImported']);self.assertNotIn('SECRET',str(snapshot))
                bot.child.terminate()
                deadline=time.monotonic()+5
                while bot.thread.is_alive() and time.monotonic()<deadline:time.sleep(.05)
                self.assertEqual(bot.snapshot()['status'],'failed');self.assertIsNone(bot.child)
                time.sleep(.1);self.assertFalse(bot.thread.is_alive())
                bot.start()
                deadline=time.monotonic()+10
                while bot.snapshot()['status']=='starting' and time.monotonic()<deadline:time.sleep(.05)
                self.assertEqual(bot.snapshot()['status'],'online')
                self.assertTrue(bot.close());self.assertIsNone(bot.child);self.assertEqual(bot.snapshot()['status'],'stopped')
                with self.assertRaises(BotError):bot.start()
            finally:bot.close();runtime.publisher.close()

    def test_missing_or_malformed_credentials_never_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime=self.runtime(Path(directory));values={};bot=DesktopBot(runtime,lambda:(values,''))
            try:
                for update in ({},{'discord_bot_token':'a b'},{'discord_bot_token':'token','vv_guild_id':'not-id'}):
                    values.clear();values.update(update)
                    with self.assertRaises(BotError):bot.start()
                    self.assertIsNone(bot.thread)
            finally:bot.close();runtime.publisher.close()

    def test_parent_eof_cancels_owned_sdk_task_and_runs_its_cleanup(self):
        async def run():
            closed=[]
            async def sdk():
                try:await asyncio.Event().wait()
                finally:closed.append(True)
            with patch('sys.stdin',io.StringIO('')):await asyncio.wait_for(owned_lifetime(sdk),2)
            self.assertEqual(closed,[True])
        asyncio.run(run())


if __name__=='__main__':unittest.main()
