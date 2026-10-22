"""Bounded session preferences, shortcut policy and next-Start schedule readback."""
import copy
import re
from service_schedule import DEFAULT_SCHEDULE, valid_rules, local_time, effective_start_settings

DEFAULTS = dict(malayalam_transliteration=False, show_malayalam_raw=False,
                desktop_transcript_display='original', smart_schedule=False,
                service_schedule=DEFAULT_SCHEDULE, schedule_timezone='system',
                desktop_panic_shortcut='Shift+Escape')


def valid_shortcut(value):
    if not isinstance(value, str) or len(value) > 60: return False
    parts = value.split('+'); modifiers = parts[:-1]; key = parts[-1]
    order = ['Control', 'Alt', 'Meta', 'Shift']
    if not modifiers or modifiers != [m for m in order if m in modifiers] or len(set(modifiers)) != len(modifiers): return False
    if not re.fullmatch(r'Escape|F(?:[1-9]|1[0-2])|[A-Z]', key): return False
    if key == 'Escape': return value == 'Shift+Escape'
    if re.fullmatch('[A-Z]', key) and ('Shift' not in modifiers or not any(m in modifiers for m in ('Control','Alt','Meta'))): return False
    if value in ('Alt+F4', 'Meta+Shift+Q', 'Control+Shift+I', 'Control+Shift+J', 'Control+Shift+C'): return False
    return True


def valid(key, value):
    if key in ('malayalam_transliteration', 'show_malayalam_raw', 'smart_schedule'): return type(value) is bool
    if key == 'desktop_transcript_display': return value in ('original', 'translation', 'transliteration') if isinstance(value, str) else False
    if key == 'desktop_panic_shortcut': return valid_shortcut(value)
    if key == 'service_schedule': return valid_rules(value)
    if key == 'schedule_timezone':
        try: local_time(timezone=value); return True
        except ValueError: return False
    return False


def project(raw):
    return {k: copy.deepcopy(raw.get(k, v) if valid(k, raw.get(k, v)) else v) for k, v in DEFAULTS.items()}


def preview(values, now=None, devices=None):
    try:
        effective, selected = effective_start_settings(values, now)
        clock = local_time(now, values.get('schedule_timezone', 'system'))
        from desktop_settings import providers_for, LANGUAGES
        problem = ''
        if effective.get('stt_engine') not in providers_for(LANGUAGES.get(effective.get('language'))): problem = 'The scheduled primary language/provider combination is unsupported.'
        elif devices is not None and effective.get('mic_index') not in {d['id'] for d in devices}: problem = 'The saved microphone is unavailable. Select an available microphone.'
        for provider in [effective.get('stt_engine')] + ([effective.get('secondary_stt_engine')] if effective.get('dual_stt_enabled') else []):
            key = {'deepgram':'deepgram_api_key','sarvam':'sarvam_api_key','gladia':'gladia_api_key','assemblyai':'assemblyai_api_key','assemblyai_pro':'assemblyai_api_key','assemblyai_multilingual':'assemblyai_api_key'}.get(provider)
            if key and not effective.get(key): problem = problem or 'Speech provider credentials are missing. Review Connections.'
        return dict(status='ready', problem=problem, timezone=values.get('schedule_timezone', 'system'),
                    clock=clock.isoformat(timespec='minutes'), selected=selected or '',
                    language=effective.get('language', ''), provider=effective.get('stt_engine', ''),
                    dual=bool(effective.get('dual_stt_enabled')), secondary_language=effective.get('secondary_language') or '',
                    secondary_provider=effective.get('secondary_stt_engine', ''),
                    message='Applies only on the next Start. The latest entry lasts until midnight; before the first entry or on other days, saved speech choices apply.')
    except ValueError:
        return dict(status='invalid', message='Schedule or time zone is unavailable. Review Settings before starting.')
