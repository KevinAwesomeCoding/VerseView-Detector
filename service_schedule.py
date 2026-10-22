"""Existing local service timetable, shared by GUI and standalone hosts.

Scheduling selects recognition settings only. It never starts an engine, saves
settings, selects a presentation target, or sends a verse.
"""
import datetime as dt
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_SCHEDULE = [dict(day=5, time='00:00', language='Malayalam'),
                    dict(day=6, time='09:10', language='English'),
                    dict(day=6, time='10:40', language='Malayalam'),
                    dict(day=6, time='16:40', language='Hindi')]


def valid_rules(rules):
    if not isinstance(rules, list) or len(rules) > 16: return False
    seen = set()
    for row in rules:
        if not isinstance(row, dict) or set(row) != {'day', 'time', 'language'}: return False
        if type(row['day']) is not int or not 0 <= row['day'] <= 6 or row['language'] not in ('English', 'Malayalam', 'Hindi'): return False
        value = row['time']
        if not isinstance(value, str) or len(value) != 5: return False
        try: parsed = dt.time.fromisoformat(value)
        except ValueError: return False
        if parsed.strftime('%H:%M') != value or (row['day'], value) in seen: return False
        seen.add((row['day'], value))
    return True


def local_time(now=None, timezone='system'):
    if not isinstance(timezone, str) or len(timezone) > 80: raise ValueError('Choose system, UTC or an available IANA time zone.')
    if timezone == 'system': return now if now is not None else dt.datetime.now().astimezone()
    try: zone = dt.timezone.utc if timezone == 'UTC' else ZoneInfo(timezone)
    except (ValueError, ZoneInfoNotFoundError): raise ValueError('That time zone is unavailable on this computer. Use system or UTC.') from None
    # Naive injected clocks represent system-local wall time, matching legacy tests.
    return (now or dt.datetime.now().astimezone()).astimezone(zone)


def scheduled_language(now=None, rules=None, timezone='system'):
    now = local_time(now, timezone)
    rules = DEFAULT_SCHEDULE if rules is None else rules
    if not valid_rules(rules): raise ValueError('Schedule entries are invalid or have duplicate day/time slots.')
    for row in sorted(rules, key=lambda r: r['time'], reverse=True):
        if row['day'] == now.weekday() and now.strftime('%H:%M') >= row['time']:
            return row['language']
    return None


def effective_start_settings(values, now=None):
    """Return a session-only copy; retain primary provider and delivery guards."""
    result = dict(values)
    language = scheduled_language(now, values.get('service_schedule'), values.get('schedule_timezone', 'system')) if values.get('smart_schedule') is True else None
    if language is None:
        return result, None
    result['language'] = language
    result['dual_stt_enabled'] = language != 'English'
    if language != 'English':
        result['secondary_language'] = 'en'
        # Match the legacy schedule's supported English secondary choices.
        if result.get('secondary_stt_engine') not in (
                'deepgram', 'assemblyai', 'assemblyai_pro', 'assemblyai_multilingual'):
            result['secondary_stt_engine'] = 'deepgram'
    return result, language
