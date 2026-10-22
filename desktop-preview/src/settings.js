(() => {
  'use strict';
  const policy = window.settingsPolicy;
  const root = document.getElementById('verseview-prototype');
  const escape = value => String(value ?? '').replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]);
  let draft = null;
  const changed = () => draft && policy.fields.some(key => JSON.stringify(draft.values[key]) !== JSON.stringify(draft.base[key]));
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
    if(!window.sessionPolicy.validRules(values.service_schedule))return 'Use up to 16 valid timetable entries without duplicate day/time slots.';
    if(!window.sessionPolicy.shortcut(values.desktop_panic_shortcut))return 'Use Shift+Escape or a supported modified shortcut. Quit/debug shortcuts are reserved.';
    if(!window.sessionPolicy.valid('schedule_timezone',values.schedule_timezone))return 'Choose system, UTC or a valid IANA time zone.';
    try {
      policy.validatePatch(values);
      if(values.watcher_passive_confidence>values.watcher_auto_confidence)return 'The watcher suggestion threshold must not exceed its high-confidence threshold.';
      if (!policy.providersFor(policy.languages[values.language]).includes(values.stt_engine)) return 'Choose a provider supported for the primary language.';
      if (values.dual_stt_enabled && (!values.secondary_language || !policy.providersFor(values.secondary_language).includes(values.secondary_stt_engine))) return 'Choose a supported secondary language and provider.';
      return '';
    } catch { return 'Check the speech and detection settings. Confidence must be 50–100%. Use an HTTP or HTTPS VerseVIEW URL without credentials or query parameters.'; }
  }
  function render(snapshot, surface = 'all') {
    sync(snapshot);
    const settings = snapshot.session?.control?.settings;
    if ((!settings || !draft) && surface === 'speech') return '<section class="vv-panel vv-detector-settings" aria-label="Live speech setup"><h2>Speech setup</h2><p class="vv-caption">Prepare your speech controls without starting listening.</p><button type="button" class="vv-btn" data-consumer-prepare="settings">Prepare speech setup</button></section>';
    const speech = surface !== 'settings', connection = surface !== 'speech';
    if (!settings || !draft) return '<section class="vv-panel vv-detector-settings"><h2>Speech and VerseVIEW settings</h2><p class="vv-caption">Choose Prepare settings above to load your microphone, language and VerseVIEW options. Listening stays stopped.</p></section>';
    const values = draft.values, control = snapshot.session.control;
    const editable = snapshot.connection === 'connected' && control.state === 'stopped' && control.actions.includes('save_settings');
    const locked = !editable || !!draft.submission;
    const error = validation(values);
    const options = (items, value) => items.map(([key, label]) => `<option value="${escape(key)}" ${key === value ? 'selected' : ''}>${escape(label)}</option>`).join('');
    const select = (key, label, items, disabled = false) => `<label>${label}<select data-detector-setting="${key}" ${locked || disabled ? 'disabled' : ''}>${options(items, values[key])}</select></label>`;
    const toggle = (key, label, description) => `<label class="vv-detection-option"><span><input type="checkbox" data-detector-setting="${key}" ${values[key] ? 'checked' : ''} ${locked ? 'disabled' : ''}> ${label}</span><span class="vv-caption">${description}</span></label>`;
    const number=(key,label,min,max,step=1)=>`<label>${label}<input type="number" data-detector-setting="${key}" min="${min}" max="${max}" step="${step}" value="${escape(values[key])}" ${locked?'disabled':''}></label>`;
    const watcher=connection?`<fieldset class="vv-detection-settings"><legend>Verse suggestions / AI watcher</legend>${toggle('watcher_enabled','Enable verse suggestions','Looks for implied passages in final speech. Every suggestion needs your explicit Display action; speech detection continues independently.')}<div class="vv-settings-grid">${select('watcher_provider','Watcher provider',Object.entries(policy.watcherProviders))}</div><p class="vv-caption">${settings.cloud?.enabled?'Your free cloud profile controls the actual English and Malayalam routes. The provider above is retained for use when that profile is off.':'Uses the selected provider and its existing configured fallback. Local AI setup is below; advanced tuning is in Developer Mode.'} Suggestions expire after 90 seconds and never display themselves.</p>${window.previewShell.isDeveloper?.()?`<details><summary>Watcher tuning</summary><div class="vv-settings-grid">${number('watcher_batch_interval','Batch interval (seconds)',1,300,.1)}${number('watcher_auto_confidence','High-confidence threshold',0,1,.01)}${number('watcher_passive_confidence','Suggestion threshold',0,1,.01)}${number('watcher_window_lines','Context window (lines)',1,100)}${number('watcher_window_seconds','Context window (seconds)',5,600)}${number('watcher_cooldown','Repeated suggestion cooldown (seconds)',0,3600)}</div><p class="vv-caption">Both confidence bands require approval. Existing free cloud budgets and minimum call spacing still apply.</p></details>`:''}</fieldset>`:'';
    const devices = settings.devices.map(item => [String(item.id), item.label]);
    if (!devices.some(([key]) => key === String(values.mic_index))) devices.unshift([String(values.mic_index), `Unavailable microphone (${values.mic_index})`]);
    return `<section class="vv-panel vv-detector-settings" aria-label="${surface === 'speech' ? 'Live speech setup' : 'Detector speech and connection settings'}"><div class="vv-panel-head"><h2>${surface === 'speech' ? 'Speech setup' : surface === 'settings' ? 'Microphone and VerseVIEW' : 'Speech and VerseVIEW settings'}</h2><span class="vv-badge">${editable ? 'Engine stopped' : 'Read only'}</span></div>
      <p class="vv-caption">Save while the engine is stopped. Changes take effect on the next start. ${surface === 'speech' ? 'Use Settings for microphone, credentials and VerseVIEW connection.' : snapshot.session?.host?.managed ? "Provider credentials and sync are in Connections below; model tuning is available in Developer Mode." : "Credentials and advanced options remain in the detector window."}</p>
      <form data-detector-settings-form novalidate><div class="vv-settings-grid">
        ${connection ? `${select('mic_index', 'Microphone', devices)}
        ${select('bible_translation', 'Bible translation', policy.bibles.map(value => [value, value]))}` : ''}
        ${speech ? `${select('language', 'Primary language', Object.keys(policy.languages).map(value => [value, value]))}
        ${select('stt_engine', 'Primary speech provider', policy.providersFor(policy.languages[values.language]).map(key => [key, policy.providers[key]]))}
        <label class="vv-settings-dual"><input type="checkbox" data-detector-setting="dual_stt_enabled" ${values.dual_stt_enabled ? 'checked' : ''} ${locked ? 'disabled' : ''}> Enable a second speech stream</label><span></span>
        ${select('secondary_language', 'Secondary language', ['en', 'ml', 'hi'].map(code => [code, Object.keys(policy.languages).find(name => policy.languages[name] === code)]), !values.dual_stt_enabled)}
        ${select('secondary_stt_engine', 'Secondary speech provider', policy.providersFor(values.secondary_language || 'en').map(key => [key, policy.providers[key]]), !values.dual_stt_enabled)}` : ''}
        ${connection ? `<label class="vv-settings-url">VerseVIEW control URL<input type="url" autocomplete="off" spellcheck="false" maxlength="512" data-detector-setting="remote_url" value="${escape(values.remote_url)}" ${locked ? 'disabled' : ''}></label>` : ''}
      </div>${connection ? `<fieldset class="vv-detection-settings"><legend>Detection behavior</legend><p class="vv-caption">These are saved settings. Save while stopped; they apply on the next Start. Speech recognition and presentation language are unchanged.</p><div class="vv-settings-grid"><label>Confidence threshold (%)<input type="number" min="50" max="100" step="0.1" data-detector-setting="confidence" value="${escape(Number((values.confidence * 100).toFixed(4)))}" ${locked ? 'disabled' : ''}><span class="vv-caption">Lower-confidence references can ask for approval. This is detection confidence, not microphone volume.</span></label>
      ${toggle('manual_confirm', 'Require manual confirmation', 'Ask before sending low-confidence detections. Clear, high-confidence references may still send automatically. When off, low-confidence detections are suppressed.')}
      ${toggle('verify', 'Require verification (hear twice)', 'The normal detection path waits for a second detection. Explicit high-confidence fast-path references can bypass this check.')}
      ${toggle('verse_interrupt', 'Verse Interrupt', 'Hold eligible verses for the spoken reading. A new reference cancels the pending verse; it expires after 60 seconds.')}
      ${toggle('spoken_numeral_mode', 'Spoken Numeral Mode', 'Interpret shorthand such as “John three seventeen” as John 3:17, without requiring the word verse.')}
      ${toggle('smart_amen', 'Smart Amen', 'Prayer wording such as “Let us pray” can clear the presentation. Listening and the app stay open.')}</div></fieldset>` : ''}${watcher}${connection?window.connectionTools?.settings(values,locked,snapshot)||'':''}${connection?window.sessionSetup?.settings(values,locked,snapshot)||'':''}${connection?`<fieldset class="vv-detection-settings"><legend>Session saving</legend>${toggle('auto_save_notes','Automatically generate and save sermon notes on Stop','Normal Stop and closing while listening save the full captured transcript first, then request notes with the configured summary provider. Emergency saves and crash checkpoints stay AI-free. Provider failures retain the transcript; completed notes and save locations are in Sermon notes.')}</fieldset>`:''}<p class="vv-caption">${surface === 'speech' ? 'Stop listening to change speech setup. Changes apply on the next start.' : snapshot.session?.host?.managed ? "If a microphone is missing, reconnect it and use Runtime in Developer Mode to restart the stopped service." : "The device list comes from the detector. Refresh microphones in its window if hardware changes."} Saving does not open a microphone or test the connection.</p>
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
    for(const field of root.querySelectorAll('[data-schedule-field],[data-schedule-add],[data-schedule-remove],[data-schedule-reset],[data-shortcut-reset]'))field.disabled=locked||(field.hasAttribute('data-schedule-add')&&draft?.values.service_schedule.length>=16);
    const button = root.querySelector('[data-save-settings]');
    if (button) button.disabled = locked || !draft || !changed() || draft.conflict || !!validation(draft.values);
  }
  function syncControls() {
    if (!draft) return;
    for (const element of root.querySelectorAll('[data-detector-setting]')) {
      const value = draft.values[element.dataset.detectorSetting];
      if (element.type === 'checkbox') element.checked = value;
      else if (element !== document.activeElement) element.value = element.dataset.detectorSetting === 'confidence' ? String(Number((value * 100).toFixed(4))) : value === null ? 'en' : String(value);
    }
  }
  function refresh() { root.dispatchEvent(new Event('preview:observer')); }
  root.addEventListener('input', event => {
    if(event.target.matches('[data-schedule-field]')&&draft){
      const e=event.target,i=Number(e.dataset.scheduleIndex),key=e.dataset.scheduleField;
      draft.values.service_schedule=draft.values.service_schedule.map((r,k)=>k===i?{...r,[key]:key==='day'?Number(e.value):e.value}:r);draft.notice='';refresh();return;
    }
    const element = event.target;
    if (!element.matches('[data-detector-setting]') || !draft || window.previewShell.getMode() !== 'observer') return;
    const key = element.dataset.detectorSetting;
    draft.values[key] = element.type === 'checkbox' ? element.checked : key === 'confidence' ? Number(element.value) / 100 : (key === 'mic_index' || key==='rate' || element.type==='number') ? Number(element.value) : element.value;
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
    if(draft&&!draft.submission){
      const b=event.target.closest('[data-schedule-add],[data-schedule-remove],[data-schedule-reset],[data-shortcut-reset]');
      if(b&&!b.disabled){
        if(b.hasAttribute('data-schedule-add'))draft.values.service_schedule=[...draft.values.service_schedule,{day:0,time:'09:00',language:'English'}];
        if(b.hasAttribute('data-schedule-remove'))draft.values.service_schedule=draft.values.service_schedule.filter((_,i)=>i!==Number(b.dataset.scheduleRemove));
        if(b.hasAttribute('data-schedule-reset'))draft.values.service_schedule=JSON.parse(JSON.stringify(window.sessionPolicy.defaults.service_schedule));
        if(b.hasAttribute('data-shortcut-reset'))draft.values.desktop_panic_shortcut='Shift+Escape';
        draft.notice='';refresh();return;
      }
    }
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
    const changes = Object.fromEntries(policy.fields.filter(key => JSON.stringify(draft.values[key]) !== JSON.stringify(draft.base[key])).map(key => [key, draft.values[key]]));
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
