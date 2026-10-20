"""Explicitly invoked, bounded probes using ONLY fixed public/synthetic text.

Never starts recognition, presentation, Discord, account setup or retries.
Confirm credential ownership/free entitlement in the account UI before invoking.
No provider is enabled on the user's saved settings by this script.
"""
import argparse
import hashlib
import json
import logging
from pathlib import Path
import sys
import threading
import time
from unittest.mock import patch

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
from free_cloud import CloudError, FreeCloudRouter, UsageLedger
from contextual_watcher import ContextualVerseWatcher, WatcherConfig

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--profile', required=True, type=Path)
parser.add_argument('--output', required=True, type=Path)
parser.add_argument('--role', required=True, choices=['verse', 'watcher', 'summary'])
parser.add_argument('--provider', required=True, choices=['groq', 'gemini', 'cloudflare'])
parser.add_argument('--model', required=True)
parser.add_argument('--start-case', type=int, default=0, help='Continue distinct watcher cases without repeating successful ones.')
parser.add_argument('--suite', choices=['basic','extended','malayalam'], default='basic')
parser.add_argument('--summary-fixture', choices=['long','multilingual-short'], default='long')
parser.add_argument('--cloudflare-credential', type=Path)
parser.add_argument('--confirmed-recurring-free-account', action='store_true', required=True)
args = parser.parse_args()
private = json.loads(args.profile.read_text(encoding='utf-8'))
credentials = {'groq': private.get('groq_api_key', ''), 'gemini': private.get('gemini_api_key', '')}
del private
if args.cloudflare_credential:
    private = json.loads(args.cloudflare_credential.read_text(encoding='utf-8'))
    credentials.update(cloudflare=private.get('cloudflare_api_token', ''),
                       cloudflare_account_id=private.get('cloudflare_account_id', ''))
    del private
args.output.parent.mkdir(parents=True, exist_ok=True)
config = {'verified_free_providers': [args.provider],
          'watcher_min_gap':10,
          'routes': {args.role: {'provider': args.provider, 'model': args.model},
                     'watcher_malayalam': {'provider': args.provider, 'model': args.model}}}
router = FreeCloudRouter(config, credentials, UsageLedger(args.output.parent / 'probe-usage.sqlite3'))
records = []
document = {'provider': args.provider, 'model': args.model, 'role': args.role,
            'input_kind': 'fixed-public-and-synthetic-only', 'cases': records}


def save():
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def record(name, callback, expected):
    start = time.monotonic()
    item = {'case': name, 'expected': expected}
    try:
        item['actual'] = callback()
        state = router.snapshot().get(args.role, {})
        if state.get('kind') not in (None, 'ok'):
            item.update(error_kind=state['kind'], error=state['message'])
    except CloudError as exc:
        item.update(error_kind=exc.kind, error=str(exc))
    item['seconds'] = round(time.monotonic()-start, 3)
    records.append(item)
    save()
    print(json.dumps({'case': name, 'seconds': item['seconds'], 'error_kind': item.get('error_kind')}) ,flush=True)
    if 'error' in item:
        raise SystemExit('Stopped on provider failure; no retry or provider substitution.')


if args.role in ('verse', 'summary'):
    # Import the actual engine without its import-time maintenance worker or file
    # logger; all outbound actions other than this router are explicitly blocked.
    with patch('logging.FileHandler', return_value=logging.NullHandler()), patch.object(threading.Thread, 'start'):
        import vv_streaming_master as engine
    engine.logger.disabled = True
    engine._free_cloud_router = router
    engine.LOCAL_LLM_ENABLED = False
    engine.LLM_ENABLED = True
    engine.current_book = engine.current_chapter = engine.current_verse = None
    engine.send_sermon_notes_to_discord = lambda _: None

if args.role == 'verse':
    cases = [
        ('english-explicit', 'Let us read John chapter three verse sixteen.', 'John 3:16'),
        ('malayalam-explicit', 'യോഹന്നാൻ മൂന്നാം അധ്യായം പതിനാറാം വാക്യം വായിക്കാം.', 'John 3:16'),
        ('english-indirect', 'For God so loved the world that he gave his only begotten Son.', None),
        ('malayalam-indirect', 'ദൈവം ലോകത്തെ സ്നേഹിച്ച് തന്റെ ഏകജാതനായ പുത്രനെ നൽകി.', None),
        ('english-negative', 'Welcome everyone. Please check the microphone and close the door.', None),
        ('malayalam-negative', 'എല്ലാവർക്കും സ്വാഗതം. മൈക്രോഫോൺ പരിശോധിക്കണം. വാതിൽ അടയ്ക്കുക.', None),
    ]
    for name, text, expected in cases:
        record(name, lambda t=text: engine.extract_verse_with_llm(t), expected)
    verse = 'For every one that doeth evil hateth the light, neither cometh to the light, lest his deeds should be reproved.'
    semantic = [
        ('english-semantic-positive', verse, True),
        ('malayalam-semantic-positive', 'ദോഷം ചെയ്യുന്നവൻ എല്ലാം വെളിച്ചത്തെ പകയ്ക്കുന്നു; തന്റെ പ്രവൃത്തികൾ വെളിപ്പെടാതിരിക്കാൻ വെളിച്ചത്തിലേക്കു വരുന്നില്ല.', True),
        ('english-semantic-announcement', 'Let us read John chapter three verse twenty.', False),
        ('malayalam-semantic-negative', 'എല്ലാവർക്കും സ്വാഗതം. മൈക്രോഫോൺ പരിശോധിക്കണം.', False),
    ]
    for name, text, expected in semantic:
        record(name, lambda t=text: engine._llm_semantic_match(verse, t, 'PUBLIC PROBE'), expected)
elif args.role == 'watcher':
    watcher = ContextualVerseWatcher(config=WatcherConfig(enabled=True))
    cases = [
        ('english-explicit', 'en', 'Let us read John chapter three verse sixteen.', 'John 3:16'),
        ('malayalam-explicit', 'ml', 'യോഹന്നാൻ മൂന്നാം അധ്യായം പതിനാറാം വാക്യം വായിക്കാം.', 'John 3:16'),
        ('english-indirect', 'en', 'For God so loved the world that he gave his only begotten Son.', 'John 3:16'),
        ('malayalam-indirect', 'ml', 'ദൈവം ലോകത്തെ സ്നേഹിച്ച് തന്റെ ഏകജാതനായ പുത്രനെ നൽകി.', 'John 3:16'),
        ('english-negative', 'en', 'Welcome everyone. Please check the microphone and close the door.', None),
        ('malayalam-negative', 'ml', 'എല്ലാവർക്കും സ്വാഗതം. മൈക്രോഫോൺ പരിശോധിക്കണം. വാതിൽ അടയ്ക്കുക.', None),
    ]
    if args.suite == 'extended':
        cases = [
            ('english-psalm-paraphrase','en','The Lord is my shepherd; I shall not want.','Psalms 23:1'),
            ('malayalam-psalm-paraphrase','ml','യഹോവ എന്റെ ഇടയനാകുന്നു; എനിക്കു മുട്ടുണ്ടാകയില്ല.','Psalms 23:1'),
            ('english-romans-paraphrase','en','All things work together for good to them that love God, to them who are called according to his purpose.','Romans 8:28'),
            ('malayalam-romans-explicit','ml','റോമർ എട്ടാം അധ്യായം ഇരുപത്തെട്ടാം വാക്യം വായിക്കാം.','Romans 8:28'),
            ('english-broad-religion','en','God is good. We should care about our community and help when someone asks.',None),
            ('malayalam-ordinary-light','ml','ഈ മുറിയിലെ വെളിച്ചം നല്ലതാണ്. ഇവിടെ മൂന്നു കസേരകൾ ഉണ്ട്.',None),
        ]
    if args.suite == 'malayalam':
        cases = [
            ('malayalam-explicit','ml','യോഹന്നാൻ മൂന്നാം അധ്യായം പതിനാറാം വാക്യം വായിക്കാം.','John 3:16'),
            ('malayalam-john-paraphrase','ml','ദൈവം ലോകത്തെ സ്നേഹിച്ച് തന്റെ ഏകജാതനായ പുത്രനെ നൽകി.','John 3:16'),
            ('malayalam-psalm-paraphrase','ml','യഹോവ എന്റെ ഇടയനാകുന്നു; എനിക്കു മുട്ടുണ്ടാകയില്ല.','Psalms 23:1'),
            ('malayalam-romans-explicit','ml','റോമർ എട്ടാം അധ്യായം ഇരുപത്തെട്ടാം വാക്യം വായിക്കാം.','Romans 8:28'),
            ('malayalam-ordinary-light','ml','ഈ മുറിയിലെ വെളിച്ചം നല്ലതാണ്. ഇവിടെ മൂന്നു കസേരകൾ ഉണ്ട്.',None),
            ('malayalam-negative','ml','എല്ലാവർക്കും സ്വാഗതം. മൈക്രോഫോൺ പരിശോധിക്കണം. വാതിൽ അടയ്ക്കുക.',None),
        ]
    for index, (name, language, text, expected) in enumerate(cases[args.start_case:]):
        if index:
            time.sleep(11)  # paced distinct test cases, never retry a failed call
        messages = [{'role': 'system', 'content': watcher._system_prompt(language)},
                    {'role': 'user', 'content': watcher._user_prompt(text)}]
        def run(messages=messages, language=language):
            result = router.complete('watcher', messages, language=language)
            return {'reply': result.choices[0].message.content, 'usage': result.usage}
        record(name, run, expected)
else:
    # Generated bilingual fixture, NOT a user's sermon. Distinct beginning/middle/
    # ending facts and omission traps support a bounded manual faithfulness check.
    engine.full_sermon_transcript = (
        'Today our title is Walking in the Light. Our passage is John 3:19-20. '
        'We are discussing why people hide wrongdoing. No speaker name was announced.\n' +
        ('The speaker repeats: truth should bring our actions into the light. '
         'This is a repeated explanation, not a new point or a new Bible reference.\n' * 180) +
        'In the middle the speaker gives an illustration of opening a curtain in a dark room. '
        'The speaker says the curtain is an illustration, not a personal story.\n' +
        ('The speaker repeats: a repeated explanation adds no new event or person.\n' * 180) +
        'At the end the speaker explicitly asks listeners to tell the truth tomorrow. '
        'There was no fundraising request, no healing testimony and no claim about a historical date.'
    )
    engine.full_sermon_transcript_secondary = (
        'ഇന്നത്തെ വിഷയം വെളിച്ചത്തിൽ നടക്കുക എന്നതാണ്. യോഹന്നാൻ 3:19-20 ആണ് വേദഭാഗം. '
        'ദോഷം ചെയ്യുന്നവൻ വെളിച്ചത്തെ പകയ്ക്കുന്നു.\n' +
        ('സത്യസന്ധത പ്രധാനമാണ്. ഇത് ആവർത്തിച്ച വിശദീകരണം മാത്രമാണ്.\n' * 180) +
        'അവസാനം നാളെ സത്യം പറയുക എന്ന് പ്രസംഗകൻ ആവശ്യപ്പെട്ടു.'
    )
    engine.verses_cited = ['John 3:19', 'John 3:20']
    if args.summary_fixture == 'multilingual-short':
        engine.full_sermon_transcript = (
            'Our title today is Small Acts of Mercy. The passage is Luke 10:33-35. '
            'The speaker says: Mercy takes time. The Samaritan stopped and helped. '
            'No speaker name was given. There was no fundraising request or healing testimony.'
        )
        engine.full_sermon_transcript_secondary = (
            'കരുണയ്ക്കു സമയം വേണം എന്ന് പ്രസംഗകൻ പറഞ്ഞു. ഈ ആഴ്ച കുടുംബത്തിലെ ഒരാളോട് ക്ഷമ ചോദിക്കണം '
            'എന്നും പറഞ്ഞു. ഒരു രോഗശാന്തി സാക്ഷ്യവും പറഞ്ഞിട്ടില്ല.'
        )
        engine.verses_cited = ['Luke 10:33', 'Luke 10:34', 'Luke 10:35']
    document['fixture'] = {'primary_chars': len(engine.full_sermon_transcript),
                           'secondary_chars': len(engine.full_sermon_transcript_secondary),
        'sha256': hashlib.sha256((engine.full_sermon_transcript + engine.full_sermon_transcript_secondary).encode()).hexdigest()}
    expected = ('Small Acts of Mercy; Luke 10:33-35; mercy takes time; ask a family member for forgiveness this week '
                '(Malayalam-only detail); no invented speaker or healing testimony.' if args.summary_fixture != 'long' else
                'Title/passage/curtain/truth-tomorrow; no invented speaker, events or references; repetitions condensed.')
    record(args.summary_fixture+'-bilingual-summary', engine.generate_sermon_summary, expected)
    record('unchanged-summary-cache', engine.generate_sermon_summary, 'same notes, no additional inference')
document['safe_status'] = router.snapshot()
save()
