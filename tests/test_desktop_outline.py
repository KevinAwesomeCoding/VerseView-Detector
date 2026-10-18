import asyncio
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from desktop_outline import SessionOutline, OutlineError
import vv_streaming_master as engine


class OutlineTests(unittest.TestCase):
    def test_model_generation_revisions_bounds_and_stop(self):
        outline=SessionOutline()
        receive,current,status=outline.prepare(True)
        self.assertEqual(current(),'')
        status('generating');receive('ആദ്യ കുറിപ്പ്')
        first=outline.snapshot()
        self.assertEqual(first['text'],'ആദ്യ കുറിപ്പ്')
        self.assertEqual(first['source'],'model')
        current();outline.edit(first['revision'],'Operator correction')
        receive('Stale generated replacement')
        self.assertEqual(outline.snapshot()['text'],'Operator correction')
        self.assertIn('skipped',outline.snapshot()['message'])
        with self.assertRaises(OutlineError):outline.edit(first['revision'],'Stale user edit')
        current();receive('x'*4001)
        self.assertEqual(outline.snapshot()['text'],'Operator correction')
        self.assertEqual(outline.snapshot()['status'],'error')
        current();receive('😀'*2001)
        self.assertEqual(outline.snapshot()['text'],'Operator correction')
        outline.cancel();receive('After Stop');status('failed')
        self.assertEqual(outline.snapshot()['status'],'stopped')
        outline.prepare(True);receive('Old session reply')
        self.assertEqual(outline.snapshot()['text'],'Operator correction')

    def test_manual_notes_work_with_ai_off_and_error_payloads_are_fixed(self):
        outline=SessionOutline()
        receive,current,status=outline.prepare(False)
        outline.edit(outline.snapshot()['revision'],'<script>plain notes</script>')
        current();receive('Unexpected AI text');status('failed')
        self.assertEqual(outline.snapshot()['text'],'<script>plain notes</script>')
        with self.assertRaises(OutlineError):outline.edit(outline.snapshot()['revision'],'\x00')

    def test_actual_outline_loop_cannot_overwrite_newer_operator_notes(self):
        async def run():
            outline=SessionOutline();receive,current,status=outline.prepare(True)
            entered,release=threading.Event(),threading.Event()
            def create(**_kwargs):
                entered.set()
                if not release.wait(3):raise RuntimeError('Test release missing')
                return engine._GroqResponse('Generated notes')
            client=SimpleNamespace(model='Fake model',chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
            stop=asyncio.Event()
            patches=dict(stop_event=stop,LIVE_POINTS_ENABLED=True,LLM_ENABLED=True,full_sermon_transcript='Synthetic speech '*30,
                         LIVE_POINTS_CALLBACK=receive,LIVE_POINTS_GET_CURRENT_CB=current,LIVE_POINTS_STATUS_CALLBACK=status,
                         _live_outline_last_dispatch=0,cerebras_client=None,groq_client=None)
            with patch.multiple(engine,**patches),patch.object(engine,'_role_has_llm',return_value=True),\
                 patch.object(engine,'_local_llm_active_for',return_value=True),patch.object(engine,'_local_client_for',return_value=client):
                task=asyncio.create_task(engine.live_points_loop(interval=.001))
                try:
                    self.assertTrue(await asyncio.to_thread(entered.wait,2))
                    outline.edit(outline.snapshot()['revision'],'Operator notes saved during generation')
                    release.set()
                    deadline=asyncio.get_running_loop().time()+2
                    while not outline.snapshot()['message'] and asyncio.get_running_loop().time()<deadline:await asyncio.sleep(.01)
                    self.assertIn('skipped',outline.snapshot()['message'])
                    self.assertEqual(outline.snapshot()['text'],'Operator notes saved during generation')
                finally:
                    release.set();stop.set();await asyncio.wait_for(task,2)
        asyncio.run(run())

    def test_stop_prevents_later_fallback_requests_or_publication(self):
        async def run():
            entered,release=threading.Event(),threading.Event()
            def create(**_kwargs):
                entered.set();release.wait(3);raise ValueError('PRIVATE-ENDPOINT')
            local=SimpleNamespace(model='Old local',chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
            old_cloud,new_cloud=Mock(),Mock();publish=Mock();stop=asyncio.Event()
            patches=dict(stop_event=stop,LIVE_POINTS_ENABLED=True,LLM_ENABLED=True,full_sermon_transcript='Synthetic speech '*30,
                         LIVE_POINTS_CALLBACK=publish,LIVE_POINTS_GET_CURRENT_CB=None,LIVE_POINTS_STATUS_CALLBACK=None,
                         _live_outline_last_dispatch=0,cerebras_client=old_cloud,groq_client=None,LOCAL_LLM_ON_FAILURE='fallback')
            with patch.multiple(engine,**patches),patch.object(engine,'_role_has_llm',return_value=True),\
                 patch.object(engine,'_local_llm_active_for',return_value=True),patch.object(engine,'_local_client_for',return_value=local),\
                 patch.object(engine,'_log_local_llm_failure'):
                task=asyncio.create_task(engine.live_points_loop(interval=.001))
                try:
                    self.assertTrue(await asyncio.to_thread(entered.wait,2))
                    engine.cerebras_client=new_cloud;stop.set();release.set()
                    await asyncio.wait_for(task,2)
                    publish.assert_not_called();old_cloud.chat.completions.create.assert_not_called();new_cloud.chat.completions.create.assert_not_called()
                finally:
                    release.set();stop.set()
                    if not task.done():await asyncio.wait_for(task,2)
        asyncio.run(run())


if __name__=='__main__':unittest.main()
