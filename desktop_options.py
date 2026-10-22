"""Typed connection and developer preferences; secrets have a write-only boundary."""
import copy
import ipaddress
import json
import math
import re
from urllib.parse import urlsplit
import settings

KEYS = ('atem_enabled','atem_ip','atem_key_duration','local_whisper_endpoint','local_llm_enabled','local_llm_endpoint',
        'local_llm_model','local_llm_timeout','local_llm_on_failure','local_llm_role_verse','local_llm_role_outline',
        'local_llm_role_summary','local_llm_model_verse','local_llm_model_outline','local_llm_model_summary',
        'local_llm_keep_alive_verse','local_llm_keep_alive_outline','local_llm_keep_alive_summary','local_llm_warm_at_start',
        'live_points_llm_enabled','live_points_prompt','llm_enabled','rate','chunk','cooldown','dedup_window',
        'silence_timeout','aai_turn_cutoff','gcp_interim_flush','vv_guild_id')
DEFAULTS = {k: settings.DEFAULTS.get(k, '') for k in KEYS}
SECRETS = ('local_llm_auth_token','local_llm_extra_headers','mistral_api_key','cerebras_api_key',
           'discord_webhook_url','discord_log_webhook_url','discord_notes_webhook_url','discord_bot_token')
BOUNDS = dict(atem_key_duration=(.1,120),local_llm_timeout=(5,180),chunk=(128,65536),cooldown=(.1,120),
              dedup_window=(1,3600),silence_timeout=(1,3600),aai_turn_cutoff=(1,60),gcp_interim_flush=(1,60))


def endpoint(v, blank=True):
    if not isinstance(v,str) or len(v)>512 or re.search(r'[\s\x00-\x1f\x7f]',v): return False
    if not v: return blank
    try:
        p=urlsplit(v)
        return p.scheme in ('http','https') and bool(p.hostname) and not p.username and not p.password and not p.query and not p.fragment and (p.port is None or 0<p.port<=65535)
    except ValueError: return False


def valid(key, v):
    if key in ('atem_enabled','local_llm_enabled','local_llm_warm_at_start','live_points_llm_enabled','llm_enabled'): return type(v) is bool
    if key in BOUNDS:
        return type(v) in (int,float) and math.isfinite(v) and BOUNDS[key][0]<=v<=BOUNDS[key][1] and (key not in ('chunk','aai_turn_cutoff','gcp_interim_flush') or type(v) is int)
    if key=='rate': return type(v) is int and v in (8000,16000,22050,24000,32000,44100,48000)
    if key=='atem_ip':
        if v=='': return True
        try: return isinstance(v,str) and ipaddress.ip_address(v).version==4
        except ValueError: return False
    if key in ('local_llm_endpoint','local_whisper_endpoint'): return endpoint(v)
    if key=='local_llm_on_failure': return v in ('fallback','skip') if isinstance(v,str) else False
    if key.startswith('local_llm_role_'): return v in ('cloud','local') if isinstance(v,str) else False
    if key.startswith('local_llm_keep_alive_'): return isinstance(v,str) and bool(re.fullmatch(r'(?:0|[1-9][0-9]{0,3})(?:s|m|h)?',v))
    if key=='live_points_prompt': return isinstance(v,str) and len(v)<=8000 and '\x00' not in v
    if key=='vv_guild_id': return isinstance(v,str) and (not v or bool(re.fullmatch(r'[0-9]{5,24}',v)))
    if key.startswith('local_llm_model'): return isinstance(v,str) and len(v)<=160 and not re.search(r'[\s\x00-\x1f\x7f]',v)
    return False


def resolved_endpoint(raw):
    value=settings.resolve_local_llm_endpoint(raw)
    candidate=value if '://' in value else 'http://'+value
    if not endpoint(candidate,False):return ''
    # Match the production request URL, including legacy host/port profiles.
    from vv_streaming_master import normalize_ollama_endpoint
    return normalize_ollama_endpoint(candidate)


def project(raw):
    result={k:copy.deepcopy(raw.get(k,d) if valid(k,raw.get(k,d)) else d) for k,d in DEFAULTS.items()}
    if not result['local_llm_endpoint']:
        resolved=resolved_endpoint(raw)
        result['local_llm_endpoint']=resolved if endpoint(resolved) else ''
    return result


def validate_secrets(values):
    from desktop_settings import SettingsError
    if not isinstance(values,dict) or not set(values)<=set(SECRETS): raise SettingsError('Unsupported connection credential field.')
    for k,v in values.items():
        if not isinstance(v,str) or len(v)>(8192 if k=='local_llm_extra_headers' else 2048) or '\x00' in v: raise SettingsError('Invalid connection credential.')
        if k=='local_llm_extra_headers':
            try: headers=json.loads(v) if v else {}
            except ValueError: raise SettingsError('Extra headers must be a JSON object.') from None
            if not isinstance(headers,dict) or len(headers)>16 or any(not isinstance(a,str) or not isinstance(b,str) or not re.fullmatch(r'[A-Za-z0-9-]{1,80}',a) or re.search(r'[\r\n\x00]',b) for a,b in headers.items()): raise SettingsError('Invalid request headers.')
        elif k.endswith('_url'):
            if v and (not endpoint(v,False) or urlsplit(v).scheme!='https'): raise SettingsError('Use a valid HTTPS webhook URL.')
        elif re.search(r'[\s\x00-\x1f\x7f]',v): raise SettingsError('Credential contains unsupported whitespace.')
    return dict(values)
