"""Secret-free cloud settings projection and validated write-only credential edits."""
import copy
import re
from urllib.parse import urlsplit, parse_qs

from free_cloud import DEFAULT_ROUTES, GROQ_MODEL

ROUTES = {
    'verse': [('groq', GROQ_MODEL)],
    'watcher': [('cloudflare', '@cf/qwen/qwen3-30b-a3b-fp8'), ('groq', GROQ_MODEL)],
    'watcher_malayalam': [('groq', GROQ_MODEL)],
    'outline': [('gemini', 'gemini-3.5-flash-lite'), ('gemini', 'gemini-3.8-flash')],
    'summary': [('gemini', 'gemini-3.5-flash-lite'), ('gemini', 'gemini-3.8-flash')],
}
CREDENTIALS = ('groq_api_key', 'gemini_api_key', 'cloudflare_api_token', 'cloudflare_account_id',
               'deepgram_api_key', 'sarvam_api_key', 'sarvam_api_key_backup',
               'assemblyai_api_key', 'gladia_api_key')
CEILINGS = {'groq': {'rpd': 1000, 'tpd': 200000},
            'cloudflare': {'rpd': 2000, 'tpd': 1000000},
            'gemini': {'rpd': 500, 'tpd': 2000000}}


def sync_url(value):
    if not isinstance(value, str) or len(value) > 2048 or re.search(r'[\s\x00-\x1f\x7f]', value):
        return False
    if not value:
        return True
    try:
        u = urlsplit(value)
        q = parse_qs(u.query, keep_blank_values=True)
        return (u.scheme == 'https' and u.hostname == 'drive.google.com' and not u.username
                and not u.password and u.port is None and not u.fragment and u.path == '/uc'
                and set(q) == {'export', 'id'} and q['export'] == ['download']
                and len(q['id']) == 1 and bool(re.fullmatch(r'[A-Za-z0-9_-]{10,200}', q['id'][0])))
    except ValueError:
        return False


def project_cloud(raw):
    config = raw.get('free_cloud_config') or {}
    routes = {}
    for role, allowed in ROUTES.items():
        default = ('groq', GROQ_MODEL) if role == 'watcher_malayalam' else DEFAULT_ROUTES[role]
        route = config.get('routes', {}).get(role, {})
        pair = (route.get('provider'), route.get('model'))
        routes[role] = '|'.join(pair if pair in allowed else default)
    limits = config.get('limits', {})
    return {'enabled': raw.get('free_cloud_enabled') is True, 'routes': routes,
            'watcher_min_gap': max(10, min(300, float(config.get('watcher_min_gap', 20)))),
            'limits': {p: {k: min(cap, max(1, int(limits.get(p, {}).get(k, cap))))
                           for k, cap in caps.items()} for p, caps in CEILINGS.items()},
            'confirmed': [p for p in CEILINGS if p in config.get('verified_free_providers', [])],
            'sync_url': raw.get('settings_sync_url', '') if sync_url(raw.get('settings_sync_url', '')) else '',
            'credentials': {key: bool(raw.get(key)) for key in CREDENTIALS}}


def validate_cloud(change, raw):
    # Never place submitted text in an exception or an observer snapshot.
    from desktop_settings import SettingsError
    def reject():
        raise SettingsError('Check cloud routes, confirmed free accounts, daily limits, Drive download URL and credential fields.')
    if not isinstance(change, dict) or not change or not set(change) <= {
            'enabled', 'routes', 'watcher_min_gap', 'limits', 'confirmed', 'sync_url', 'credentials'}:
        reject()
    view = project_cloud(raw)
    merged = {**view, **change}
    if type(merged['enabled']) is not bool or type(merged['watcher_min_gap']) not in (int, float) or not 10 <= merged['watcher_min_gap'] <= 300:
        reject()
    if not isinstance(merged['confirmed'], list) or any(p not in CEILINGS for p in merged['confirmed']):
        reject()
    if not isinstance(merged['routes'], dict) or set(merged['routes']) != set(ROUTES):
        reject()
    routes = {}
    for role, value in merged['routes'].items():
        if not isinstance(value, str) or value not in ['|'.join(pair) for pair in ROUTES[role]]:
            reject()
        provider, model = value.split('|')
        if merged['enabled'] and provider not in merged['confirmed']:
            reject()
        routes[role] = {'provider': provider, 'model': model}
    if not sync_url(merged['sync_url']) or not isinstance(merged['limits'], dict) or set(merged['limits']) != set(CEILINGS):
        reject()
    for provider, caps in CEILINGS.items():
        values = merged['limits'][provider]
        if not isinstance(values, dict) or set(values) != set(caps):
            reject()
        if any(type(values[k]) is not int or not 1 <= values[k] <= cap for k, cap in caps.items()):
            reject()
    credentials = change.get('credentials', {})
    if not isinstance(credentials, dict) or not set(credentials) <= set(CREDENTIALS):
        reject()
    for key, value in credentials.items():
        if not isinstance(value, str) or not 1 <= len(value) <= 512 or re.search(r'[\s\x00-\x1f\x7f]', value):
            reject()
        if key == 'cloudflare_account_id' and not re.fullmatch('[a-fA-F0-9]{32}', value):
            reject()
    updated = copy.deepcopy(raw.get('free_cloud_config') or {})
    updated['routes'] = {**updated.get('routes', {}), **routes}
    updated['verified_free_providers'] = list(dict.fromkeys(merged['confirmed']))
    updated['watcher_min_gap'] = merged['watcher_min_gap']
    limits = updated.setdefault('limits', {})
    for provider, values in merged['limits'].items():
        limits[provider] = {**limits.get(provider, {}), **values}
    return {'free_cloud_enabled': merged['enabled'], 'free_cloud_config': updated,
            'settings_sync_url': merged['sync_url'], **credentials}
