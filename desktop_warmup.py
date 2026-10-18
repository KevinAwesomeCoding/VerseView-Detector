"""One opt-in warmup worker per owned host; no model metadata in public status."""
import copy
import logging
import math
import threading

ROLES = ('verse', 'outline', 'summary', 'watcher')
STATES = ('off', 'skipped', 'running', 'complete', 'failed', 'cancelled', 'busy')


def public_status(value):
    if not isinstance(value, dict) or value.get('status') not in STATES:
        return None
    rows = []
    for row in (value.get('roles') if isinstance(value.get('roles'), list) else [])[:4]:
        if not isinstance(row, dict) or row.get('role') not in ROLES or row.get('status') not in ('warmed', 'failed'):
            continue
        elapsed = row.get('elapsed_seconds')
        rows.append(dict(role=row['role'], status=row['status'], elapsed_seconds=
                         round(min(86400, max(0, elapsed)), 2) if type(elapsed) in (int, float) and math.isfinite(elapsed) else 0))
    total = value.get('total', 0)
    return dict(status=value['status'], total=min(4, max(0, total)) if type(total) is int else 0, roles=rows)


class SessionWarmup:
    def __init__(self):
        self.lock = threading.RLock()
        self.thread = None
        self.cancelled = threading.Event()
        self.generation = 0
        self.value = dict(status='off', total=0, roles=[])

    def snapshot(self):
        with self.lock:
            return copy.deepcopy(self.value)

    def start(self, engine, enabled, stopped=False):
        """Capture configured clients now. A later configure cannot change this pass.

        An in-flight synchronous HTTP call cannot be cancelled. Stop prevents
        subsequent roles/results; a quick restart skips warmup while that call
        finishes instead of spawning overlapping warmup workers. Recognition
        never waits for this worker. Existing per-client timeouts still apply.
        """
        is_stopped = stopped if callable(stopped) else lambda: stopped
        with self.lock:
            self.cancelled.set()
            self.generation += 1
            generation = self.generation
            self.value = dict(status='off', total=0, roles=[])
            if not enabled:
                return
            if is_stopped():
                self.value['status'] = 'cancelled'
                return
            if self.thread and self.thread.is_alive():
                self.value['status'] = 'busy'
                return
            clients = {role: client for role, client in dict(engine.local_llm_clients).items()
                       if role in ROLES} if engine.LOCAL_LLM_ENABLED else {}
            if not clients:
                self.value['status'] = 'skipped'
                return
            cancelled = self.cancelled = threading.Event()
            self.value = dict(status='running', total=len(clients), roles=[])
            self.thread = threading.Thread(target=self._run, args=(engine, clients, cancelled, generation, is_stopped),
                                           name='VerseViewWarmup', daemon=True)
            self.thread.start()

    def _run(self, engine, clients, cancelled, generation, is_stopped):
        def cancelled_now():
            return cancelled.is_set() or is_stopped()
        def record(result):
            role, ok, _private_message, elapsed = result
            with self.lock:
                if generation != self.generation or cancelled_now():
                    return
                row = public_status(dict(status='running', total=len(clients), roles=[
                    dict(role=role, status='warmed' if ok else 'failed', elapsed_seconds=elapsed)]))['roles']
                self.value['roles'].extend(row)
        try:
            engine.warm_all_local_llm_roles(clients=clients, cancelled=cancelled_now, on_result=record)
            with self.lock:
                if generation == self.generation:
                    self.value['status'] = ('cancelled' if cancelled_now() else
                        'failed' if any(row['status'] == 'failed' for row in self.value['roles']) else 'complete')
        except Exception:
            logging.getLogger(__name__).exception('Local model warmup failed; details retained in the private log')
            with self.lock:
                if generation == self.generation and not cancelled_now():
                    self.value['status'] = 'failed'

    def cancel(self):
        with self.lock:
            self.cancelled.set()
            if self.value['status'] == 'running':
                self.value['status'] = 'cancelled'
