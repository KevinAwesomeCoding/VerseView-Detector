"""Opt-in, fail-closed cloud routing. No SDKs, retries, paid fallback or key rotation.

The local ledger is shared by streams, roles and processes using this profile.
It contains numeric usage only, never prompts, replies, keys or account IDs.
Published limits are ceilings, not entitlement checks: activation also requires
an explicit confirmation of a recurring free account in private settings.
"""
from collections import OrderedDict
from contextlib import closing
from dataclasses import dataclass
import hashlib
import json
import logging
import math
from pathlib import Path
import re
import sqlite3
import threading
import time
from types import SimpleNamespace

import certifi
import requests

log = logging.getLogger(__name__)
GROQ_MODEL = 'qwen/qwen3.8-27b'
DEFAULT_ROUTES = {
    'verse': ('groq', GROQ_MODEL),
    'watcher': ('cloudflare', '@cf/qwen/qwen3-30b-a3b-fp8'),
    'outline': ('gemini', 'gemini-3.5-flash-lite'),
    'summary': ('gemini', 'gemini-3.5-flash-lite'),
    'translation': ('groq', GROQ_MODEL),
}
# Source links and account observations: docs/FREE_CLOUD_API_AUDIT.md.
# (context, RPM, RPD, TPM, TPD, input/output neurons per million tokens)
MODELS = {
    ('groq', GROQ_MODEL): (131072, 30, 1000, 8000, 200000, 0, 0),
    ('cloudflare', '@cf/meta/llama-3.1-8b-instruct-fp8-fast'):
        (8192, 30, 2000, 100000, 1000000, 4119, 34868),
    ('cloudflare', '@cf/qwen/qwen3-30b-a3b-fp8'):
        (32768, 30, 2000, 100000, 1000000, 4625, 30475),
    ('gemini', 'gemini-3.5-flash-lite'): (1048576, 15, 500, 250000, 2000000, 0, 0),
    ('gemini', 'gemini-3.8-flash'): (1048576, 5, 20, 250000, 2000000, 0, 0),
}
OUTPUT_CAPS = {'verse': 48, 'watcher': 220, 'translation': 256,
               'outline': 1500, 'summary': 6000}
ROLE_DAILY_CAPS = {'verse': 1000, 'watcher': 1200, 'translation': 300,
                   'outline': 120, 'summary': 20}


class CloudError(RuntimeError):
    """Only constructed from safe fixed text; raw HTTP exceptions never escape."""
    def __init__(self, kind, detail):
        self.kind = kind
        super().__init__(detail)


def response(content, usage=None):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
                           usage=usage or {})


def input_bound(messages):
    """Conservative UTF-8 byte bound, including chat framing; not a tokenizer.

    Deliberately less permissive for Malayalam than chars/4. Gemini summaries
    additionally use countTokens; complete transcripts are never truncated.
    """
    return 32 + sum(32 + len(m['content'].encode('utf-8')) for m in messages)


@dataclass(frozen=True)
class Limits:
    rpm: int
    rpd: int
    tpm: int
    tpd: int
    neurons: float = 9000  # leave 10% of Cloudflare's 10K allocation unused


class UsageLedger:
    def __init__(self, path, clock=time.time):
        self.path, self.clock = str(path), clock
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS calls '
                       '(id INTEGER PRIMARY KEY, ts REAL, provider TEXT, model TEXT, '
                       'role TEXT, inp INTEGER, out INTEGER, neurons REAL)')
            db.execute('CREATE TABLE IF NOT EXISTS holds '
                       '(provider TEXT, model TEXT, until REAL, kind TEXT, '
                       'PRIMARY KEY(provider,model))')
            db.execute('CREATE TABLE IF NOT EXISTS remaining '
                       '(provider TEXT PRIMARY KEY, ts REAL, requests INTEGER, tokens INTEGER)')

    def connect(self):
        return sqlite3.connect(self.path, timeout=5)

    def reserve(self, provider, model, role, inp, out, neurons, limits, watcher_gap=10):
        now = self.clock()
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM calls WHERE ts < ?', (now - 172800,))
            hold = db.execute('SELECT until,kind FROM holds WHERE provider=? AND model=?',
                              (provider, model)).fetchone()
            if hold and hold[0] > now:
                raise CloudError(hold[1], f'{provider}: {hold[1]} hold; check account or wait '
                                 f'{math.ceil(hold[0]-now)} seconds before another attempt.')
            rows = db.execute('SELECT ts,provider,model,role,inp+out,neurons FROM calls '
                              'WHERE ts > ?', (now - 86400,)).fetchall()
            pool = [r for r in rows if r[1] == provider and
                    (provider in ('groq', 'cloudflare') or r[2] == model)]
            minute = [r for r in pool if r[0] > now - 60]
            # These are rolling 24h caps, intentionally conservative across each
            # provider's differing calendar reset time. Stops/starts don't refill.
            reserve_req = 200 if provider == 'groq' and role != 'verse' else 0
            reserve_tok = 40000 if reserve_req else 0
            reserve_rpm = 10 if reserve_req else 0
            reserve_tpm = 3000 if reserve_req else 0
            remote = db.execute('SELECT ts,requests,tokens FROM remaining WHERE provider=?', (provider,)).fetchone()
            if remote:
                # Groq headers report RPD remaining and TPM remaining. Keep the
                # observation for 24h / 60s respectively, including other apps'
                # consumption. Deduct subsequent local reservations as well.
                after = [r for r in pool if r[0] >= remote[0]]
                if (now - remote[0] < 86400 and remote[1] is not None and
                        remote[1] - len(after) <= reserve_req):
                    raise CloudError('quota', f'{provider}: server-reported daily capacity is reserved or exhausted.')
                if (now - remote[0] < 60 and remote[2] is not None and
                        remote[2] - sum(r[4] for r in after) < inp + out + reserve_tpm):
                    raise CloudError('rate', f'{provider}: server-reported minute capacity is reserved or exhausted.')
            if (len(pool) + 1 > limits.rpd - reserve_req or
                    sum(r[4] for r in pool) + inp + out > limits.tpd - reserve_tok or
                    (provider == 'cloudflare' and sum(r[5] for r in pool) + neurons > limits.neurons)):
                raise CloudError('quota', f'{provider}: daily free budget reached; optional work paused. '
                                 'Wait for usage to age out; do not add billing or rotate keys.')
            if (len(minute) + 1 > limits.rpm - reserve_rpm or
                    sum(r[4] for r in minute) + inp + out > limits.tpm - reserve_tpm):
                raise CloudError('rate', f'{provider}: minute budget reached; wait for capacity. '
                                 'Verse capacity is reserved before optional work.')
            if sum(r[3] == role for r in rows) >= ROLE_DAILY_CAPS[role]:
                raise CloudError('quota', f'{role}: daily feature cap reached; wait before generating more.')
            if role == 'watcher' and any(r[3] == 'watcher' and r[0] > now - watcher_gap for r in rows):
                raise CloudError('rate', 'Watcher global dispatch limit: wait for the next slot across both streams.')
            cur = db.execute('INSERT INTO calls(ts,provider,model,role,inp,out,neurons) '
                             'VALUES(?,?,?,?,?,?,?)', (now, provider, model, role, inp, out, neurons))
            return cur.lastrowid

    def reconcile(self, reservation, inp, out, neurons):
        with closing(self.connect()) as db, db:
            db.execute('UPDATE calls SET inp=?,out=?,neurons=? WHERE id=?',
                       (inp, out, neurons, reservation))

    def hold(self, provider, model, seconds, kind):
        with closing(self.connect()) as db, db:
            db.execute('INSERT OR REPLACE INTO holds VALUES(?,?,?,?)',
                       (provider, model, self.clock() + seconds, kind))

    def observe_groq(self, headers):
        def integer(name):
            try: return max(0, int(headers[name]))
            except (ValueError, TypeError, KeyError): return None
        remaining_requests = integer('x-ratelimit-remaining-requests')
        tokens = integer('x-ratelimit-remaining-tokens')
        if remaining_requests is not None or tokens is not None:
            with closing(self.connect()) as db, db:
                db.execute('INSERT OR REPLACE INTO remaining VALUES(?,?,?,?)',
                           ('groq', self.clock(), remaining_requests, tokens))


class FreeCloudRouter:
    def __init__(self, config, credentials, ledger, post=requests.post, clock=time.time):
        self.config, self.credentials, self.ledger = config or {}, credentials, ledger
        self.post, self.clock = post, clock
        self.lock, self.cache = threading.RLock(), OrderedDict()
        self.role_locks = {role: threading.Lock() for role in DEFAULT_ROUTES}
        self.last_status = {}

    def route(self, role, language=''):
        malayalam_watcher = role == 'watcher' and str(language).lower().startswith('ml')
        route_key = 'watcher_malayalam' if malayalam_watcher else role
        route = self.config.get('routes', {}).get(route_key, {})
        provider, model = ('groq', GROQ_MODEL) if malayalam_watcher else DEFAULT_ROUTES[role]
        provider, model = route.get('provider', provider), route.get('model', model)
        if (provider, model) not in MODELS:
            raise CloudError('model', 'This provider/model is outside the reviewed recurring-free allowlist.')
        if provider not in self.config.get('verified_free_providers', []):
            raise CloudError('entitlement', f'{provider}: confirm recurring free plan, project/model quotas '
                             'and credential ownership before enabling this route.')
        if not self.credentials.get(provider):
            raise CloudError('auth', f'{provider}: configure the private API credential before enabling this route.')
        if provider == 'cloudflare' and not re.fullmatch('[0-9a-fA-F]{32}',
                str(self.credentials.get('cloudflare_account_id', ''))):
            raise CloudError('auth', 'Cloudflare: configure the correct account ID and a Workers AI scoped token.')
        return provider, model

    def available(self, role):
        try:
            self.route(role)
            return True
        except CloudError as exc:
            self.status(role, exc)
            return False

    def status(self, role, exc):
        value = {'kind': exc.kind, 'message': str(exc)}
        with self.lock:
            changed = self.last_status.get(role) != value
            self.last_status[role] = value
        if changed:
            log.warning('Free cloud %s: %s', role, exc)

    def snapshot(self):
        with self.lock:
            return {role: dict(value) for role, value in self.last_status.items()}

    def _json(self, provider, model, url, headers, body, timeout):
        operation = 'token count' if url.endswith(':countTokens') else 'completion'
        try:
            result = self.post(url, headers=headers, json=body, timeout=timeout,
                               verify=certifi.where(), allow_redirects=False)
        except requests.RequestException:
            raise CloudError('transport', f'{provider} {operation}: connection failed; check network/TLS and try manually.') from None
        if result.status_code != 200:
            code = result.status_code
            kind = {401: 'auth', 403: 'permission', 402: 'quota', 404: 'model',
                    429: 'rate'}.get(code, 'transport')
            # Only inspect provider text for classification; never include it in logs.
            if code == 429 and any(t in result.text.lower() for t in ('quota', 'daily', 'per day', 'exhausted')):
                kind = 'quota'
            try:
                delay = max(60, min(86400, float(result.headers.get('retry-after', '60'))))
            except (ValueError, TypeError):
                delay = 60
            if kind in ('auth', 'permission', 'model', 'quota'):
                delay = 86400
            self.ledger.hold(provider, model, delay, kind)
            hint = {'auth': 'check the credential', 'permission': 'check project/model permissions',
                    'model': 'check current model availability', 'quota': 'wait for the free quota reset',
                    'rate': 'wait for the rate limit reset'}.get(kind, 'check provider/network status')
            raise CloudError(kind, f'{provider} {operation}: HTTP {code}; {hint}. No retry or provider switch was made.')
        if provider == 'groq':
            self.ledger.observe_groq(result.headers)
        try:
            return result.json()
        except (ValueError, TypeError):
            raise CloudError('invalid', f'{provider}: response was not valid JSON.') from None

    def complete(self, role, messages, temperature=0.1, max_tokens=None, cache_key=None, language=''):
        acquired = False
        try:
            # A timed-out watcher executor may still be finishing its HTTP call.
            # Do not queue another cloud call behind it (or issue it after Stop).
            acquired = self.role_locks[role].acquire(blocking=role != 'watcher')
            if not acquired:
                raise CloudError('busy', 'Watcher previous request is still finishing; this cycle was skipped.')
            return self._complete(role, messages, temperature, max_tokens, cache_key, language)
        except CloudError as exc:
            self.status(role, exc)
            raise
        except (sqlite3.Error, OSError):
            exc = CloudError('budget', 'Free usage ledger unavailable; repair the profile before making cloud calls.')
            self.status(role, exc)
            raise exc from None
        finally:
            if acquired:
                self.role_locks[role].release()

    def _complete(self, role, messages, temperature, max_tokens, cache_key, language):
        provider, model = self.route(role, language)
        cap = min(OUTPUT_CAPS[role], max_tokens or OUTPUT_CAPS[role])
        signature = hashlib.sha256(json.dumps([provider, model, role, temperature, cap,
                    cache_key if cache_key is not None else messages], sort_keys=True).encode()).hexdigest()
        # Calls for a role share a lock across streams. Verse has its own lock.
        # Cached content is memory-only and bounded to 64 results.
        with self.lock:
            cached = self.cache.get(signature)
            ttl = 86400 if role == 'summary' else 40
            if cached and self.clock() - cached[0] < ttl:
                return response(cached[1], {'cached': True})
        context, rpm, rpd, tpm, tpd, ni, no = MODELS[(provider, model)]
        # A user can lower ceilings, never raise the reviewed free limits.
        limits = self.config.get('limits', {}).get(provider, {})
        limit = Limits(*(min(v, max(1, int(limits.get(k, v)))) for k, v in
                         [('rpm', rpm), ('rpd', rpd), ('tpm', tpm), ('tpd', tpd)]))
        inp = input_bound(messages)
        counted_summary = provider == 'gemini' and role == 'summary'
        if not counted_summary and (inp + cap > context or inp + cap > limit.tpm):
            raise CloudError('context', f'{provider}: complete input exceeds the conservative context/minute '
                             'budget. Shorten the input or explicitly select another verified free route; no text was dropped.')
        if counted_summary:
            # Reserve the entire permissible input budget while countTokens is
            # in flight. An actual token count can admit a long bilingual input
            # that the UTF-8 byte bound alone would conservatively reject.
            inp = min(inp, min(context, limit.tpm) - cap)
        neurons = (inp * ni + cap * no) / 1000000
        reservation = self.ledger.reserve(provider, model, role, inp, cap, neurons, limit,
                                         max(10, float(self.config.get('watcher_min_gap', 20))))
        key = self.credentials[provider]
        headers = {'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}
        body = {'model': model, 'messages': messages, 'temperature': temperature, 'max_tokens': cap}
        timeout = 90 if role == 'summary' else 30
        if provider == 'gemini':
            headers = {'x-goog-api-key': key, 'Content-Type': 'application/json'}
            root = 'https://generativelanguage.googleapis.com/v1beta/models/' + model
            contents = [{'role': 'user' if m['role'] != 'assistant' else 'model',
                         'parts': [{'text': m['content']}]} for m in messages if m['role'] != 'system']
            system = '\n'.join(m['content'] for m in messages if m['role'] == 'system')
            native = {'contents': contents}
            if system:
                native['systemInstruction'] = {'parts': [{'text': system}]}
            if role == 'summary':
                counted = self._json(provider, model, root + ':countTokens', headers,
                                     {'generateContentRequest': {'model': 'models/' + model, **native}}, timeout)
                total = counted.get('totalTokens')
                if type(total) is not int or total + cap > min(context, limit.tpm):
                    raise CloudError('context', 'Gemini: token count missing or complete transcript exceeds limits.')
                self.ledger.reconcile(reservation, total, cap, 0)
            native['generationConfig'] = {'temperature': temperature, 'maxOutputTokens': cap,
                'thinkingConfig': {'thinkingLevel': 'MINIMAL' if model.endswith('flash-lite') else 'LOW'}}
            data = self._json(provider, model, root + ':generateContent', headers, native, timeout)
            try:
                candidate = data['candidates'][0]
                if candidate.get('finishReason') != 'STOP':
                    raise CloudError('incomplete', 'Gemini: blocked or truncated output; result was not accepted.')
                content = ''.join(p.get('text', '') for p in candidate['content']['parts'] if not p.get('thought'))
                usage = data.get('usageMetadata', {})
                actual_in = usage.get('promptTokenCount')
                actual_out = usage.get('candidatesTokenCount', 0) + usage.get('thoughtsTokenCount', 0)
            except (KeyError, IndexError, TypeError):
                raise CloudError('invalid', 'Gemini: no usable text completion.') from None
        else:
            if provider == 'groq':
                url = 'https://api.groq.com/openai/v1/chat/completions'
                body['reasoning_effort'] = 'none'
            else:
                account = self.credentials['cloudflare_account_id']
                url = f'https://api.cloudflare.com/client/v4/accounts/{account}/ai/v1/chat/completions'
                if model == '@cf/qwen/qwen3-30b-a3b-fp8':
                    # Cloudflare's Qwen chat template supports /no_think.
                    body['messages'] = [*messages, {'role': 'user', 'content': '/no_think'}]
            data = self._json(provider, model, url, headers, body, timeout)
            try:
                choice = data['choices'][0]
                if choice.get('finish_reason') != 'stop':
                    raise CloudError('incomplete', f'{provider}: truncated output; result was not accepted.')
                content = choice['message']['content']
                usage = data.get('usage', {})
                actual_in, actual_out = usage.get('prompt_tokens'), usage.get('completion_tokens')
            except (KeyError, IndexError, TypeError):
                raise CloudError('invalid', f'{provider}: no usable text completion.') from None
        if not isinstance(content, str) or not content.strip():
            raise CloudError('invalid', f'{provider}: empty completion; result was not accepted.')
        if type(actual_in) is int and actual_in >= 0 and type(actual_out) is int and actual_out >= 0:
            self.ledger.reconcile(reservation, actual_in, actual_out,
                                  (actual_in * ni + actual_out * no) / 1000000)
        with self.lock:
            self.last_status[role] = {'kind': 'ok', 'message': f'{provider}/{model}: completed'}
            self.cache[signature] = (self.clock(), content)
            while len(self.cache) > 64:
                self.cache.popitem(last=False)
        return response(content, usage)

    def watcher_client(self):
        router = self
        class Completions:
            def create(self, model, messages, **kwargs):
                return router.complete('watcher', messages, **kwargs)
        return SimpleNamespace(chat=SimpleNamespace(completions=Completions()), free_cloud=True)
