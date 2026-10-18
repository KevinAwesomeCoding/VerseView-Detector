(() => {
  'use strict';
  const policy = window.settingsPolicy;
  const root = document.getElementById('verseview-prototype');
  const escape = value => String(value ?? '').replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]);
  let draft = null;
  const changed = () => draft && policy.fields.some(key => draft.values[key] !== draft.base[key]);
  function sync(snapshot) {
    const control = snapshot.session?.control, settings = control?.settings;
    if (!settings) return;
    if (!draft || draft.hostId !== control.id) {
      draft = { hostId: control.id, revision: settings.revision, base: { ...settings.values }, values: { ...settings.values }, notice: '', conflict: false, submission: null };
    }
    const result = control.results.find(item => item.id === draft.submission?.id);
    if (result) {
      draft.submission = null;
      draft.notice = result.reason;
      if (result.outcome === 'saved') {
        draft.base = { ...settings.values }; draft.values = { ...settings.values };
        draft.revision = settings.revision; draft.conflict = false;
      }
    }
    if (settings.revision !== draft.revision) {
      if (changed()) draft.conflict = true;
      else { draft.base = { ...settings.values }; draft.values = { ...settings.values }; draft.revision = settings.revision; draft.conflict = false; }
    }
  }
  function validation(values) {
    try {
      policy.validatePatch(values);
      if (!policy.providersFor(policy.languages[values.language]).includes(values.stt_engine)) return 'Choose a provider supported for the primary language.';
      if (values.dual_stt_enabled && (!values.secondary_language || !policy.providersFor(values.secondary_language).includes(values.secondary_stt_engine))) return 'Choose a supported secondary language and provider.';
      return '';
    } catch { return 'Check the microphone, languages, providers and VerseVIEW URL. Use an HTTP or HTTPS URL without credentials or query parameters.'; }
  }
  function render(snapshot) {
    sync(snapshot);
    const settings = snapshot.session?.control?.settings;
    if (!settings || !draft) return '<section class="vv-panel vv-detector-settings"><h2>Speech and VerseVIEW settings</h2><p class="vv-caption">Settings require the updated detector with desktop controls enabled. Credentials and advanced options remain in its existing window.</p></section>';
    const values = draft.values, control = snapshot.session.control;
    const editable = snapshot.connection === 'connected' && control.state === 'stopped' && control.actions.includes('save_settings');
    const locked = !editable || !!draft.submission;
    const error = validation(values);
    const options = (items, value) => items.map(([key, label]) => `<option value="${escape(key)}" ${key === value ? 'selected' : ''}>${escape(label)}</option>`).join('');
    const select = (key, label, items, disabled = false) => `<label>${label}<select data-detector-setting="${key}" ${locked || disabled ? 'disabled' : ''}>${options(items, values[key])}</select></label>`;
    const devices = settings.devices.map(item => [String(item.id), item.label]);
    if (!devices.some(([key]) => key === String(values.mic_index))) devices.unshift([String(values.mic_index), `Unavailable microphone (${values.mic_index})`]);
    return `<section class="vv-panel vv-detector-settings" aria-label="Detector speech and connection settings"><div class="vv-panel-head"><h2>Speech and VerseVIEW settings</h2><span class="vv-badge">${editable ? 'Engine stopped' : 'Read only'}</span></div>
      <p class="vv-caption">Save while the engine is stopped. Changes take effect on the next start. ${snapshot.session?.host?.managed ? "Credentials and advanced options are in the private backend settings file." : "Credentials and advanced options remain in the detector window."}</p>
      <form data-detector-settings-form novalidate><div class="vv-settings-grid">
        ${select('mic_index', 'Microphone', devices)}
        ${select('bible_translation', 'Bible translation', policy.bibles.map(value => [value, value]))}
        ${select('language', 'Primary language', Object.keys(policy.languages).map(value => [value, value]))}
        ${select('stt_engine', 'Primary speech provider', policy.providersFor(policy.languages[values.language]).map(key => [key, policy.providers[key]]))}
        <label class="vv-settings-dual"><input type="checkbox" data-detector-setting="dual_stt_enabled" ${values.dual_stt_enabled ? 'checked' : ''} ${locked ? 'disabled' : ''}> Enable a second speech stream</label><span></span>
        ${select('secondary_language', 'Secondary language', ['en', 'ml', 'hi'].map(code => [code, Object.keys(policy.languages).find(name => policy.languages[name] === code)]), !values.dual_stt_enabled)}
        ${select('secondary_stt_engine', 'Secondary speech provider', policy.providersFor(values.secondary_language || 'en').map(key => [key, policy.providers[key]]), !values.dual_stt_enabled)}
        <label class="vv-settings-url">VerseVIEW control URL<input type="url" autocomplete="off" spellcheck="false" maxlength="512" data-detector-setting="remote_url" value="${escape(values.remote_url)}" ${locked ? 'disabled' : ''}></label>
      </div><p class="vv-caption">${snapshot.session?.host?.managed ? "Close and relaunch the stopped backend to refresh its microphone list." : "The device list comes from the detector. Refresh microphones in its window if hardware changes."} Saving does not open a microphone or test the connection.</p>
      <p class="vv-caption vv-settings-message" role="status" aria-live="polite" data-settings-status>${escape(draft.conflict ? 'Settings changed elsewhere. Reload to review the latest values before saving.' : draft.submission ? 'Saving settings; waiting for the detector to acknowledge.' : draft.notice || error || (changed() ? 'Unsaved changes.' : 'No unsaved changes.'))}</p>
      <div class="vv-control-actions"><button type="submit" class="vv-btn vv-btn-primary" data-save-settings ${locked || !changed() || draft.conflict || error ? 'disabled' : ''}>Save settings</button><button type="button" class="vv-btn" data-reload-settings ${draft.submission ? 'disabled' : ''}>Reload settings</button></div></form></section>`;
  }
  function updateAvailability(snapshot) {
    sync(snapshot);
    const control = snapshot.session?.control;
    const locked = snapshot.connection !== 'connected' || control?.state !== 'stopped'
      || !control?.settings || !control.actions.includes('save_settings') || !!draft?.submission;
    for (const field of root.querySelectorAll('[data-detector-setting]')) {
      field.disabled = locked || (['secondary_language', 'secondary_stt_engine'].includes(field.dataset.detectorSetting) && !draft?.values.dual_stt_enabled);
    }
    const button = root.querySelector('[data-save-settings]');
    if (button) button.disabled = locked || !draft || !changed() || draft.conflict || !!validation(draft.values);
  }
  function syncControls() {
    if (!draft) return;
    for (const element of root.querySelectorAll('[data-detector-setting]')) {
      const value = draft.values[element.dataset.detectorSetting];
      if (element.type === 'checkbox') element.checked = value;
      else if (element !== document.activeElement) element.value = value === null ? 'en' : String(value);
    }
  }
  function refresh() { root.dispatchEvent(new Event('preview:observer')); }
  root.addEventListener('input', event => {
    const element = event.target;
    if (!element.matches('[data-detector-setting]') || !draft || window.previewShell.getMode() !== 'observer') return;
    const key = element.dataset.detectorSetting;
    draft.values[key] = element.type === 'checkbox' ? element.checked : key === 'mic_index' ? Number(element.value) : element.value;
    draft.notice = '';
    if (key === 'dual_stt_enabled' && draft.values[key] && !draft.values.secondary_language) draft.values.secondary_language = 'en';
    if (key === 'dual_stt_enabled' && !draft.values[key]) draft.values.secondary_language = null;
    if (key === 'language' || key === 'secondary_language' || key === 'dual_stt_enabled') {
      const role = key === 'language' ? 'stt_engine' : 'secondary_stt_engine';
      const allowed = policy.providersFor(key === 'language' ? policy.languages[draft.values.language] : draft.values.secondary_language || 'en');
      if (!allowed.includes(draft.values[role])) draft.values[role] = allowed[0];
    }
    refresh();
  });
  root.addEventListener('click', event => {
    if (!event.target.closest('[data-reload-settings]') || draft?.submission) return;
    draft = null; refresh();
  });
  root.addEventListener('submit', async event => {
    if (!event.target.matches('[data-detector-settings-form]')) return;
    event.preventDefault();
    const snapshot = window.previewShell.getObserver();
    sync(snapshot);
    if (!draft || draft.submission || draft.conflict || validation(draft.values) || !changed()
      || snapshot.connection !== 'connected' || snapshot.session?.control?.state !== 'stopped') return;
    const changes = Object.fromEntries(policy.fields.filter(key => draft.values[key] !== draft.base[key]).map(key => [key, draft.values[key]]));
    const owner = draft;
    owner.submission = { id: null }; refresh();
    try {
      const result = await window.verseviewDesktop.saveSettings(snapshot.session.session_id, owner.revision, changes);
      owner.submission = result;
      setTimeout(() => {
        if (owner.submission?.id === result.id) {
          sync(window.previewShell.getObserver());
          if (owner.submission?.id === result.id) { owner.submission = null; owner.notice = 'Save outcome unknown. Check or reload the detector settings before trying again.'; }
          refresh();
        }
      }, 12000);
    } catch (error) { owner.submission = null; owner.notice = error.message; }
    refresh();
  });
  window.detectorSettings = Object.freeze({ render, syncControls, updateAvailability });
})();
