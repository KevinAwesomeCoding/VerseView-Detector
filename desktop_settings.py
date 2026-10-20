"""Non-secret desktop settings projection and stopped-engine settings transaction."""
import copy
import hashlib
import json
import re
import threading
from urllib.parse import urlsplit
import uuid

LANGUAGES = {'English': 'en', 'Malayalam': 'ml', 'Hindi': 'hi', 'Multi-Language': 'multi'}
PROVIDERS = {'deepgram': 'Deepgram', 'sarvam': 'Sarvam AI',
             'assemblyai_pro': 'AssemblyAI (Universal-3 Pro)',
             'assemblyai_multilingual': 'AssemblyAI (Universal-3 Multilingual)',
             'gladia': 'Gladia', 'gcp': 'Google Cloud STT', 'local_whisper': 'Local Whisper'}
BIBLES = ['KJV', 'WEB', 'ASV', 'NET', 'NLT', 'NIV', 'ESV', 'NASB', 'NKJV', 'AMP', 'CSB', 'MSG', 'OEB', 'WEBBE']
FIELDS = {'language', 'stt_engine', 'dual_stt_enabled', 'secondary_language',
          'secondary_stt_engine', 'mic_index', 'remote_url', 'bible_translation'}


class SettingsError(ValueError):
    pass


def providers_for(language):
    allowed = ['deepgram', 'gladia', 'gcp', 'local_whisper']
    if language in ('ml', 'hi'):
        allowed.insert(1, 'sarvam')
    if language == 'ml':
        allowed.remove('deepgram')
    if language == 'en':
        allowed[1:1] = ['assemblyai_pro', 'assemblyai_multilingual']
    if language == 'multi':
        allowed.insert(1, 'assemblyai_multilingual')
    return allowed


def valid_url(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 512 or re.search(r'\s|[\x00-\x1f\x7f]', value):
        return False
    try:
        parsed = urlsplit(value)
        return (parsed.scheme in ('http', 'https') and bool(parsed.hostname) and not parsed.username
                and not parsed.password and not parsed.query and not parsed.fragment
                and (parsed.port is None or 1 <= parsed.port <= 65535))
    except ValueError:
        return False


def project(raw):
    """Explicit allowlist: never export a settings dictionary or provider credentials."""
    language = {'Hindi Nova-3': 'Hindi', 'Hindi Sarvam AI': 'Hindi'}.get(raw.get('language'), raw.get('language'))
    provider = lambda key: 'assemblyai_pro' if raw.get(key) == 'assemblyai' else raw.get(key)
    return {'language': language if language in LANGUAGES else '',
            'stt_engine': provider('stt_engine') if provider('stt_engine') in PROVIDERS else '',
            'dual_stt_enabled': raw.get('dual_stt_enabled') is True,
            'secondary_language': raw.get('secondary_language') if raw.get('secondary_language') in ('en', 'ml', 'hi') else None,
            'secondary_stt_engine': provider('secondary_stt_engine') if provider('secondary_stt_engine') in PROVIDERS else '',
            'mic_index': raw.get('mic_index') if type(raw.get('mic_index')) is int else -1,
            'remote_url': raw.get('remote_url') if valid_url(raw.get('remote_url')) else '',
            'bible_translation': str(raw.get('bible_translation', '')).upper() if str(raw.get('bible_translation', '')).upper() in BIBLES else ''}


def validate_changes(changes, current, devices):
    if not isinstance(changes, dict) or not changes or not set(changes) <= FIELDS:
        raise SettingsError('Only the displayed connection and speech settings can be changed.')
    for key, value in changes.items():
        if key == 'dual_stt_enabled':
            valid = type(value) is bool
        elif key == 'mic_index':
            valid = type(value) is int
        elif key == 'secondary_language':
            valid = value is None or isinstance(value, str)
        else:
            valid = isinstance(value, str)
        if not valid:
            raise SettingsError('Invalid settings value.')
    result = dict(current)
    result.update(changes)
    if result['language'] not in LANGUAGES or result['stt_engine'] not in providers_for(LANGUAGES[result['language']]):
        raise SettingsError('Choose a supported primary language and provider combination.')
    if type(result['dual_stt_enabled']) is not bool or result['secondary_language'] not in (None, 'en', 'ml', 'hi'):
        raise SettingsError('Choose a valid secondary language and dual speech setting.')
    if result['secondary_stt_engine'] not in PROVIDERS:
        raise SettingsError('Choose a supported secondary provider.')
    if result['dual_stt_enabled'] and (not result['secondary_language'] or result['secondary_stt_engine'] not in providers_for(result['secondary_language'])):
        raise SettingsError('Choose a supported secondary language and provider combination.')
    if type(result['mic_index']) is not int or result['mic_index'] < 0 or (result['mic_index'] != current['mic_index'] and result['mic_index'] not in {row['id'] for row in devices}):
        raise SettingsError('That microphone is unavailable. Refresh the detector device list.')
    if not valid_url(result['remote_url']):
        raise SettingsError('Use an HTTP or HTTPS VerseVIEW URL without credentials, query parameters, or a fragment.')
    if result['bible_translation'] not in BIBLES:
        raise SettingsError('Choose a supported Bible translation.')
    return {key: result[key] for key in changes}


class DesktopSettings:
    """Only refresh/save access GUI fields; both are called on the GUI thread."""
    def __init__(self, read, apply):
        self.read, self.apply = read, apply
        self.lock = threading.Lock()
        self.signature, self.raw, self.view = None, None, None
        self.refresh()

    def refresh(self):
        try:
            raw = self.read()
            devices = [{'id': row['id'], 'label': str(row['label'])[:160]} for row in raw['devices'][:256]
                       if type(row.get('id')) is int and row['id'] >= 0]
            signature = hashlib.sha256(json.dumps(raw, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            with self.lock:
                revision = self.view['revision'] if self.signature == signature and self.view else uuid.uuid4().hex
                self.raw, self.signature = raw, signature
                from desktop_cloud_settings import project_cloud
                self.view = {'revision': revision, 'values': project(raw['values']), 'devices': devices,
                             'cloud': project_cloud(raw['values'])}
        except Exception:
            with self.lock:
                self.raw, self.signature, self.view = None, None, None

    def snapshot(self):
        with self.lock:
            return copy.deepcopy(self.view)

    def save(self, revision, changes):
        self.refresh()
        with self.lock:
            if not self.view:
                raise SettingsError('Settings are unavailable. Check detector settings.')
            if revision != self.view['revision']:
                raise SettingsError('Settings changed elsewhere. Reload the form before saving.')
            if isinstance(changes, dict) and set(changes) == {'cloud_settings'}:
                from desktop_cloud_settings import validate_cloud
                checked = validate_cloud(changes['cloud_settings'], self.raw['values'])
            else:
                checked = validate_changes(changes, self.view['values'], self.view['devices'])
            storage_revision = self.raw.get('storage_revision')
        self.apply(checked, storage_revision)
        self.refresh()


class GuiSettings:
    """Uses the legacy GUI fields and existing settings store without reloading the GUI."""
    def __init__(self, gui, config):
        self.gui, self.config = gui, config

    def storage(self):
        path = self.config._settings_path()
        if not path.exists():
            return {}, 'missing'
        data = path.read_bytes()
        value = json.loads(data)
        if not isinstance(value, dict):
            raise SettingsError('Settings file is invalid.')
        return value, hashlib.sha256(data).hexdigest()

    def read(self):
        _, revision = self.storage()
        return {'values': self.gui._collect_settings(), 'storage_revision': revision,
                'devices': [{'id': index, 'label': label} for label, index in self.gui.mic_map.items()]}

    def widgets(self, values):
        gui = self.gui
        gui.lang_var.set(values['language'])
        gui.stt_engine_var.set(PROVIDERS[values['stt_engine']])
        gui.stt_engine_menu.configure(values=[PROVIDERS[key] for key in providers_for(LANGUAGES[values['language']])])
        gui.dual_stt_var.set(values['dual_stt_enabled'])
        if values['secondary_language']:
            gui.sec_lang_var.set(next(name for name, code in LANGUAGES.items() if code == values['secondary_language']))
        gui.sec_engine_var.set(PROVIDERS[values['secondary_stt_engine']])
        gui.sec_engine_menu.configure(values=[PROVIDERS[key] for key in providers_for(values['secondary_language'] or LANGUAGES.get(gui.sec_lang_var.get(), 'en'))])
        state = 'normal' if values['dual_stt_enabled'] else 'disabled'
        gui.sec_lang_menu.configure(state=state)
        gui.sec_engine_menu.configure(state=state)
        match = next((label for label, index in gui.mic_map.items() if index == values['mic_index']), None)
        if match:
            gui.mic_var.set(match)
        gui.bible_var.set(values['bible_translation'])
        gui.url_entry.delete(0, 'end')
        gui.url_entry.insert(0, values['remote_url'])
        gui.ml_raw_cb.configure(state='normal' if values['language'] == 'Malayalam' else 'disabled')
        gui.ml_translit_cb.configure(state='normal' if values['language'] == 'Malayalam' else 'disabled')
        gui._set_dual_log_view(values['dual_stt_enabled'])
        gui._update_log_headers()

    def apply(self, changes, expected_storage):
        gui = self.gui
        if gui._running or gui._closing:
            raise SettingsError('Stop the engine before changing settings.')
        saved, revision = self.storage()
        if revision != expected_storage:
            raise SettingsError('Settings changed elsewhere. Reload the form before saving.')
        before = gui._collect_settings()
        before_safe = project(before)
        updated = {**before_safe, **changes}
        variable_names = ['lang_var', 'stt_engine_var', 'dual_stt_var', 'sec_lang_var',
                          'sec_engine_var', 'mic_var', 'bible_var']
        variables = [(getattr(gui, name), getattr(gui, name).get()) for name in variable_names]
        menu_properties = [('stt_engine_menu', ('values',)), ('sec_engine_menu', ('values', 'state')),
                           ('sec_lang_menu', ('state',)), ('ml_raw_cb', ('state',)), ('ml_translit_cb', ('state',))]
        menus = [(getattr(gui, name), {key: getattr(gui, name).cget(key) for key in keys})
                 for name, keys in menu_properties]
        old_url = gui.url_entry.get()
        try:
            self.widgets(updated)
            # A dashboard save never commits unrelated legacy GUI drafts or credentials.
            merged = {**self.config.DEFAULTS, **saved, **updated}
            merged['bible_translation'] = merged['bible_translation'].lower()
            if not self.config.save(merged):
                raise SettingsError('Could not save settings.')
        except Exception:
            try:
                for variable, value in variables:
                    variable.set(value)
                for menu, properties in menus:
                    menu.configure(**properties)
                gui.url_entry.delete(0, 'end')
                gui.url_entry.insert(0, old_url)
                gui._set_dual_log_view(before_safe['dual_stt_enabled'])
                gui._update_log_headers()
            except Exception:
                raise SettingsError('Settings save failed. Check the detector window before continuing.') from None
            raise SettingsError('Could not apply settings. Previous values were retained.') from None
        gui._s = {**gui._s, **updated}
        gui._s["bible_translation"] = updated["bible_translation"].lower()
