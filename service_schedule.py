"""Existing local service timetable, shared by GUI and standalone hosts.

Scheduling selects recognition settings only. It never starts an engine, saves
settings, selects a presentation target, or sends a verse.
"""
import datetime as dt


def scheduled_language(now=None):
    now = now if now is not None else dt.datetime.now()
    if now.weekday() == 5:
        return 'Malayalam'
    if now.weekday() == 6:
        for threshold, language in ((dt.time(16, 40), 'Hindi'),
                                    (dt.time(10, 40), 'Malayalam'),
                                    (dt.time(9, 10), 'English')):
            if now.time() >= threshold:
                return language
    return None


def effective_start_settings(values, now=None):
    """Return a session-only copy; retain primary provider and delivery guards."""
    result = dict(values)
    language = scheduled_language(now) if values.get('smart_schedule') is True else None
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
