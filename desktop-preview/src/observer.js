(() => {
  'use strict';
  const escape = value => String(value ?? '').replace(/[&<>"']/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[character]);
  let command = null;
  let recoveryOpen = null;
  let suggestionsOpen = null;
  const languageNames = { en: 'English', ml: 'Malayalam', hi: 'Hindi', multi: 'Multilingual' };
  const outcomeNames = { COMMAND_ACCEPTED: 'Command accepted', SUPPRESSED: 'Suppressed',
    MANUAL_CONFIRM_REQUIRED: 'Awaiting operator approval', QUEUED: 'Queued', CANCELLED: 'Cancelled',
    EXPIRED: 'Expired', ERROR: 'Error', DELIVERY_FAILED: 'Delivery failed', DETECTED: 'Candidate detected' };
  const time = value => value ? `<time datetime="${escape(value)}" title="${escape(value)}">${escape(new Date(value).toLocaleTimeString())}</time>` : 'Not received';
  const outcome = value => outcomeNames[value] || value.replaceAll('_', ' ').toLowerCase();
  const streamName = (session, role) => role === 'unknown' ? 'Unattributed stream'
    : `${role === 'primary' ? 'Primary' : 'Secondary'} · ${languageNames[session.config.streams[role].language] || session.config.streams[role].language || 'Language not reported'}`;

  function reconcileCommand(snapshot){
    const control=snapshot.session?.control;
    if(command?.hostId&&control&&command.hostId!==control.id)command=null;
    const result=control?.results.find(item=>item.id===command?.id);
    if(result)command={...result,hostId:control.id};
  }

  function controlPanel(snapshot) {
    const session = snapshot.session;
    const control = session?.control;
    if (!control) return '<p class="vv-caption vv-observer-note">Read-only connection. Engine controls remain in the existing detector.</p>';
    reconcileCommand(snapshot);
    const enabled = snapshot.connection === 'connected';
    const disabled = !enabled || command?.outcome === 'submitted';
    const commandLabels = { submitted: 'Request sent', requested: 'Request acknowledged', answered: 'Decision acknowledged', prepared: 'Recovery prepared', discarded: 'Recovery discarded', rejected: 'Request rejected', failed: 'Request failed', unknown: 'Outcome unknown' };
    const notice = command ? `${commandLabels[command.outcome] || command.outcome}. ${command.reason || 'Waiting for the detector to acknowledge.'}` : 'Start uses the existing detector settings. Approval returns to the existing delivery checks.';
    return recoveryPanel(snapshot, disabled) + `<section class="vv-panel vv-engine-control" aria-label="Detector controls"><div class="vv-panel-head"><div><h2>Detector controls</h2><p class="vv-caption">${escape(control.state)} · PID ${session.pid}</p></div><div class="vv-control-actions">${['start', 'stop', ...(control.actions.includes('panic') ? ['panic'] : [])].map(action => `<button type="button" class="vv-btn ${action === 'start' ? 'vv-btn-primary' : ''}" data-engine-action="${action}" data-engine-session="${session.session_id}" ${disabled || !control.actions.includes(action) ? 'disabled' : ''}>${action === 'start' ? 'Start engine' : action === 'panic' ? 'Clear output' : 'Stop engine'}</button>`).join('')}</div></div>
      <p class="vv-caption" role="status" aria-live="polite" data-command-status>${escape(enabled ? notice : 'Connection unavailable. Commands disabled; showing the last snapshot.')}</p>
      ${control.pending.length ? `<div class="vv-pending-list"><h3>Awaiting your decision</h3>${control.pending.map(item => `<div class="vv-pending-candidate"><div><strong>${escape(item.reference)}</strong><p class="vv-caption">${Math.round(item.confidence * 100)}% confidence · ${escape(streamName(session, item.stream))} · ${escape(item.source)}</p><code>${escape(item.candidate_id)}</code></div><div class="vv-control-actions">${['approve', 'reject'].map(action => `<button type="button" class="vv-btn ${action === 'approve' ? 'vv-btn-primary' : ''}" data-engine-action="${action}" data-engine-session="${session.session_id}" data-candidate="${escape(item.candidate_id)}" ${disabled ? 'disabled' : ''}>${action === 'approve' ? 'Approve' : 'Reject'} ${escape(item.reference)}</button>`).join('')}</div></div>`).join('')}</div>` : '<p class="vv-caption">No candidates awaiting approval.</p>'}</section>` + suggestionPanel(snapshot, disabled);
  }

  function suggestionPanel(snapshot, disabled) {
    const session=snapshot.session, control=session.control, value=control.suggestions;
    if(!value?.enabled)return '';
    const stateLabel={sending:'Send in progress',accepted:'Command accepted',review:'No acceptance confirmed · inspect delivery activity',unknown:'Outcome unknown after Stop · inspect delivery activity'};
    return `<details class="vv-panel vv-suggestions" data-suggestion-panel data-suggestion-session="${session.session_id}" ${suggestionsOpen===session.session_id?'open':''}><summary>Verse suggestions · ${value.rows.length}</summary>
      <div class="vv-suggestions-body"><p class="vv-caption">${value.active ? value.has_clients ? `Watcher active · ${value.cycles} cycles` : 'Watcher active · no provider client configured' : 'Watcher stopped'} · ${value.suggested} suggestions · ${value.discarded} discarded. Advice expires after 90 seconds. Sends use the existing delivery checks.</p>
      ${value.rows.length ? value.rows.slice().reverse().map(row=>`<div class="vv-pending-candidate"><div><strong>${escape(row.reference)}</strong><p class="vv-caption">${Math.round(row.confidence*100)}% · ${escape(streamName(session,row.stream))} · ${time(row.created_at)}</p><p class="vv-caption">${escape(row.state==='available' ? row.kind==='auto_suggest' ? 'Automatic candidate · inspect delivery activity for its result' : 'Suggested passage · awaiting your choice' : stateLabel[row.state])}</p>${row.reasoning?`<p class="vv-caption">${escape(row.reasoning)}</p>`:''}${row.candidate_id?`<code>${escape(row.candidate_id)}</code>`:''}</div><button type="button" class="vv-btn" data-engine-action="send_suggestion" data-engine-session="${session.session_id}" data-suggestion-id="${row.id}" ${disabled||!control.actions.includes('send_suggestion')||!value.active||value.busy||row.state!=='available'?'disabled':''}>Send ${escape(row.reference)}</button></div>`).join('') : '<p class="vv-caption">No current suggestions.</p>'}</div></details>`;
  }

  function recoveryPanel(snapshot, disabled) {
    const session = snapshot.session, control = session.control, value = control.recovery;
    if (!value || !['available', 'staged', 'invalid'].includes(value.status)) {
      return value?.message ? `<p class="vv-caption" role="status">${escape(value.message)}</p>` : '';
    }
    const preview = value.preview;
    return `<section class="vv-panel vv-recovery" aria-label="Saved session recovery"><div class="vv-panel-head"><h2>${value.status === 'staged' ? 'Session ready to resume' : value.status === 'invalid' ? 'Saved session needs attention' : 'Saved session available'}</h2></div>
      <div class="vv-recovery-body"><p class="vv-caption">${value.status === 'staged' ? 'Saved context is prepared. Press Start to resume recognition.' : value.status === 'invalid' ? escape(value.message) : 'Restore saved sermon context or discard it to start fresh. Recognition is stopped.'} Nothing is presented by this choice.</p>
      ${value.saved_at ? `<p class="vv-caption">Saved ${time(value.saved_at)} · ${escape(value.reason)} · ${value.verse_count} history entries</p>` : ''}
      ${preview ? `<details data-recovery-preview data-recovery-key="${control.id}-${value.revision}" ${recoveryOpen === `${control.id}-${value.revision}` ? 'open' : ''}><summary>Saved content preview</summary><p class="vv-caption">Historical preview · up to 2,000 characters per stream. Full engine context is kept in the private recovery file.</p><div class="vv-dual-grid">${['primary', 'secondary'].map(role => `<div><h3>${role === 'primary' ? 'Primary' : 'Secondary'} · ${escape(languageNames[preview.languages[role]] || 'Language not recorded')}</h3><p class="vv-caption">${preview.sources[role] === 'speech' ? 'Saved final speech' : 'Saved engine context · may be translated'}</p><p class="vv-recovery-text" lang="${preview.sources[role] === 'speech' ? escape(preview.languages[role]) : 'und'}">${escape(preview[role] || 'No saved text for this stream.')}</p></div>`).join('')}</div>${preview.references.length ? `<p class="vv-caption">Recent history: ${preview.references.map(escape).join(' · ')}</p>` : ''}</details>` : ''}
      <div class="vv-control-actions">${['restore_session', 'discard_session'].filter(action => value.status !== 'invalid' || action === 'discard_session').map(action => `<button type="button" class="vv-btn ${action === 'restore_session' ? 'vv-btn-primary' : ''}" data-engine-action="${action}" data-engine-session="${session.session_id}" data-recovery-revision="${escape(value.revision)}" ${disabled || !control.actions.includes(action) ? 'disabled' : ''}>${action === 'restore_session' ? 'Restore saved session' : 'Discard saved session'}</button>`).join('')}</div></div></section>`;
  }

  function backendPanel() {
    const value = window.previewShell.getBackend();
    const busy = ['starting', 'closing'].includes(value.status);
    const session = window.previewShell.getObserver().session;
    const sync=session?.control?.sync;
    return `<section class="vv-backend-status" aria-label="Bundled backend status"><div><strong>${value.status === 'unavailable' ? 'External detector connection' : 'Standalone backend preview'}</strong><p class="vv-caption">${escape(value.status === 'unavailable' ? 'This build has no native companion. An updated external detector can still publish the feed.' : value.message)}${value.pid ? ` · PID ${value.pid}` : ''}</p>${session?.host?.notice ? `<p class="vv-caption">${escape(session.host.notice)}</p>` : ''}${sync&&['pulling','failed','conflict'].includes(sync.status)?`<p class="vv-caption" data-backend-sync-notice>${escape(sync.message)}</p>`:''}${warmupStatus(session?.host?.warmup)}</div><div class="vv-control-actions">${value.owned ? '<button type="button" class="vv-btn" data-backend-action="folder">Open backend settings folder</button><button type="button" class="vv-btn" data-backend-action="close">Close backend</button>' : value.status !== 'unavailable' ? '<button type="button" class="vv-btn" data-backend-action="launch">Launch bundled backend</button>' : ''}${busy ? '<span class="vv-caption">Please wait…</span>' : ''}</div></section>`;
  }

  function warmupStatus(value) {
    if (!value || value.status === 'off') return '';
    const labels = { skipped:'No local model roles are configured for warmup.',
      running:`Warming local models · ${value.roles.length} of ${value.total} roles finished. Recognition can continue.`,
      complete:'Local model warmup completed.', failed:'Local model warmup finished with errors. Inspect the private backend log.',
      cancelled:'Local model warmup stopped. An in-flight request may still finish.',
      busy:'Warmup skipped for this start while a previous request finishes.' };
    const roles = { verse:'Verse detection', outline:'Outline', summary:'Summary', watcher:'Watcher' };
    return `<p class="vv-caption" data-warmup-status="${value.status}" role="status">${escape(labels[value.status])}${value.roles.length ? `<br>${value.roles.map(row => `${roles[row.role]}: ${row.status} (${row.elapsed_seconds.toFixed(1)}s)`).join(' · ')}` : ''}</p>`;
  }

  function status(snapshot) {
    reconcileCommand(snapshot);
    const session = snapshot.session;
    return backendPanel() + `<section class="vv-observer-status" aria-label="Observer connection status" data-connection="${escape(snapshot.connection)}">
      <div><strong>${escape(snapshot.message)}</strong><p class="vv-caption">${session
        ? `${session.origin === 'callback-replay' ? 'Callback replay · no microphone audio' : 'Detector event feed'} · PID ${session.pid} · Engine ${escape(session.engine_state.replaceAll('_', ' '))}`
        : 'Start the updated detector with its local observer export enabled. Engine controls require the updated detector and explicit desktop-control opt-in.'}</p></div>
      ${snapshot.sources.length > 1 || snapshot.selected ? `<label>Detector process<select data-observer-source aria-label="Observed detector process"><option value="" ${!snapshot.selected ? 'selected' : ''}>Automatic · one active process</option>${snapshot.sources.map(source => `<option value="${source.session_id}" ${snapshot.selected === source.session_id ? 'selected' : ''}>PID ${source.pid} · ${source.origin === 'callback-replay' ? 'replay' : 'detector'} · ${source.fresh ? source.engine_state : 'stale'}</option>`).join('')}</select></label>` : ''}
    </section>`;
  }

  function streamPanel(session, role) {
    const config = session?.config.streams[role];
    const language = config?.language || '';
    const name = languageNames[language] || language || `${role === 'primary' ? 'Primary' : 'Secondary'} speech`;
    const label = language === 'ml' ? 'മലയാളം' : name;
    const full = window.transcriptView?.isFull() === true;
    const lines = full ? window.transcriptView.rows(session, role) : session?.transcripts.filter(row => row.stream === role && row.is_final).slice(-4) || [];
    const partial = session?.transcripts.filter(row => row.stream === role && !row.is_final).at(-1);
    const lastEvent = session?.delivery_events.filter(row => row.stream === role && row.reference).at(-1);
    const streamState = session?.streams[role]?.state;
    const streamStatus = config?.enabled === false ? 'Disabled in detector' : ({ configured: 'Configured',
      starting: 'Starting in detector', transcript_received: 'Transcript received', stopped: 'Stream stopped', error: 'Stream error'
    })[streamState] || 'Waiting for status';
    return `<section class="vv-panel vv-stream vv-observed-stream" data-speech-stream="${role}" aria-label="${escape(name)} observed speech">
      <div class="vv-stream-header"><div><h2 lang="${escape(language || 'und')}">${escape(label)}</h2><p class="vv-stream-provider">${role === 'primary' ? 'Primary' : 'Secondary'} · ${escape(config?.provider || 'Provider not reported')}</p></div><span class="vv-badge">${escape(streamStatus)}</span></div>
      <div class="vv-stream-results ${full ? 'vv-full-transcript' : ''}" ${full ? `data-full-transcript="${role}" tabindex="0" aria-label="${escape(name)} full transcript"` : ''}>${lines.length ? lines.map(row => `<div class="vv-transcript-line"><span class="vv-transcript-time">${time(row.timestamp)}</span><p lang="${escape(row.language || 'und')}">${escape(row.text)}</p>${row.translation && row.translation !== row.text ? `<details class="vv-caption"><summary>English translation</summary><p lang="en">${escape(row.translation)}</p></details>` : ''}</div>`).join('') : '<p class="vv-observer-empty">No final transcript received.</p>'}</div>
      ${partial ? `<div class="vv-partial"><span class="vv-caption">Interim transcript</span><p lang="${escape(partial.language || 'und')}">${escape(partial.text)}</p></div>` : ''}
      <div class="vv-ref-notice">${lastEvent ? `<span><span class="vv-ref-notice-label">Latest reported candidate outcome</span><span class="vv-ref-notice-ref">${escape(lastEvent.reference)}</span></span><span class="vv-badge">${escape(outcome(lastEvent.outcome))}</span>` : '<span class="vv-caption">No reference outcome reported for this stream.</span>'}</div>
    </section>`;
  }

  function output(session) {
    const accepted = session?.delivery_events.filter(event => event.outcome === 'COMMAND_ACCEPTED').at(-1);
    return `<section class="vv-panel vv-output" aria-label="Last reported accepted command"><div class="vv-output-top"><span class="vv-eyebrow">Last accepted command</span><span class="vv-badge">Visible output unverified</span></div>
      <div class="vv-output-ref">${accepted ? escape(accepted.reference) : 'No accepted command reported'}</div>
      <p class="vv-caption vv-observer-output-note">${accepted ? `The engine reports command acceptance at ${time(accepted.timestamp)}. Verse text and the visible VerseVIEW screen are not supplied by this feed.` : 'Detected or held references will not be shown as accepted commands.'}</p>
      <div class="vv-output-foot"><span>${accepted ? escape(streamName(session, accepted.stream)) : 'Read-only observation'}</span><span>${accepted ? escape(accepted.candidate_id) : 'No presentation controls'}</span></div></section>`;
  }

  function sessionView(snapshot, layout) {
    const session = snapshot.session;
    const transcripts = `<section class="vv-stream-section" aria-label="Observed speech streams"><div class="vv-dual-grid">${streamPanel(session, 'primary')}${streamPanel(session, 'secondary')}</div></section>`;
    const unknown = session?.transcripts.filter(row => row.stream === 'unknown').slice(-3) || [];
    return status(snapshot) + controlPanel(snapshot) + (window.transcriptView?.controls(session) || '') + (window.transcriptView?.isFull() ? transcripts : layout.endsWith('focus') ? output(session) + transcripts : transcripts + output(session))
      + (unknown.length ? `<section class="vv-panel vv-observer-unknown"><h2>Unattributed speech</h2>${unknown.map(row => `<p>${escape(row.text)}</p>`).join('')}</section>` : '')
      + `<p class="vv-caption vv-observer-note">${session?.host?.managed ? 'The bundled detector owns recognition and delivery. Advanced queue and presentation options are in its private backend settings file.' : 'The detector owns recognition and delivery. Queue and presentation settings remain in its existing window.'}</p>`;
  }

  function activity(snapshot) {
    const session = snapshot.session;
    return status(snapshot) + controlPanel(snapshot) + `<section class="vv-panel" aria-label="Observed delivery activity"><div class="vv-panel-head"><h2>Engine delivery events</h2><span class="vv-pill">Read only</span></div>${session?.delivery_events.length ? session.delivery_events.slice().reverse().map(event => `<div class="vv-activity-item"><span class="vv-dot"></span><div><div class="vv-activity-title">${escape(event.reference || 'No reference')} · ${escape(outcome(event.outcome))}</div><div class="vv-activity-meta">${escape(streamName(session, event.stream))} · ${escape(event.language)} · ${escape(event.source)}<br>${escape(event.candidate_id)} · ${escape(event.stage)} · ${escape(event.outcome)}</div><p class="vv-activity-why">${escape(event.reason)}</p></div><span class="vv-time">${time(event.timestamp)}</span></div>`).join('') : '<p class="vv-observer-empty">No delivery events received. Nothing here establishes visible presentation output.</p>'}</section>`;
  }

  function settings(snapshot) {
    const session = snapshot.session;
    const managed = session?.host?.managed;
    const bible = session?.config.bible_translation;
    const savedBible = session?.control?.settings?.values?.bible_translation;
    return status(snapshot) + window.cloudSettings.render(snapshot) + syncPanel(snapshot) + botPanel(snapshot) + window.detectorSettings.render(snapshot) + `<section class="vv-panel preview-about" aria-label="Observer setup"><h2>Local detector connection</h2>
      <p class="vv-caption">${managed ? "This dashboard owns the bundled backend and its private preview profile. The installed detector has not been replaced." : "The preview reads structured snapshots from your local VerseView/Observer folder. The installed detector has not been replaced."}</p>
      <p class="vv-caption">${managed ? 'Use the engine controls to start or stop recognition. Speech and connection settings can be saved above while recognition is stopped. Cloud providers and credential sync can be configured above while recognition is stopped.' : 'An updated detector must be started with <code>VERSEVIEW_OBSERVER=1</code> to publish the feed. Also set <code>VERSEVIEW_DESKTOP_CONTROL=1</code> to enable start/stop and candidate decisions. Without that opt-in the connection stays read only. Speech and connection settings can be saved above while stopped; credentials and advanced options remain in the detector.'}</p>
      <p class="vv-caption">${session ? `Session ${escape(session.session_id)} · ${bible ? `Engine Bible translation: ${escape(bible)}` : savedBible ? `Saved Bible translation: ${escape(savedBible)} · applies on Start` : 'Bible setting: not reported'}` : 'No observer session selected.'}</p></section>`;
  }

  function syncPanel(snapshot){
    const session=snapshot.session,value=session?.control?.sync;
    if(!value)return '';
    return `<section class="vv-panel vv-bot-panel" data-sync-panel aria-label="Settings sync"><div class="vv-panel-head"><h2>Settings sync</h2><span class="vv-badge" data-sync-status>${escape(value.status)}</span></div>
      <p class="vv-caption" role="status">${escape(value.message)}</p><p class="vv-caption">${value.configured?'Private sync URL configured.':'Set the Drive download link in Cloud providers above.'} Only supported credential fields are pulled. Recognition, presentation and other settings stay as saved. Stop recognition and the bot before pulling.</p>
      ${value.completed_at?`<p class="vv-caption">Last completed pull: ${time(value.completed_at)} · ${value.updated_count} credential field(s) changed.</p>`:''}
      <button type="button" class="vv-btn" data-engine-action="pull_settings" data-engine-session="${session.session_id}" ${snapshot.connection!=='connected'||!session.control.actions.includes('pull_settings')||command?.outcome==='submitted'?'disabled':''}>Pull credentials now</button>
      ${command?.action==='pull_settings'?`<p class="vv-caption">${escape(command.reason||'Waiting for acknowledgement.')}</p>`:''}</section>`;
  }

  function botPanel(snapshot){
    const session=snapshot.session,control=session?.control,bot=control?.bot;
    if(!bot)return '';
    const disabled=snapshot.connection!=='connected'||command?.outcome==='submitted';
    return `<section class="vv-panel vv-bot-panel" data-bot-panel aria-label="Discord bot controls"><div class="vv-panel-head"><h2>Discord bot</h2><span class="vv-badge" data-bot-status>${escape(bot.status)}</span></div>
      <p class="vv-caption">${escape(bot.message)}${bot.pid?` · Owned PID ${bot.pid}`:''}</p>
      ${['start_bot','stop_bot'].includes(command?.action)?`<p class="vv-caption" role="status">${escape(command.reason||'Waiting for the detector to acknowledge.')}</p>`:''}
      <p class="vv-caption">${bot.configured?'Private credentials configured.':'Add discord_bot_token to the private backend settings file.'} Start connects Discord; stopping the bot leaves recognition running. Commands control this preview’s backend.</p>
      <div class="vv-control-actions">${['start_bot','stop_bot'].map(action=>`<button type="button" class="vv-btn" data-engine-action="${action}" data-engine-session="${session.session_id}" ${disabled||!control.actions.includes(action)?'disabled':''}>${action==='start_bot'?'Start bot':'Stop bot'}</button>`).join('')}</div>
      ${bot.events.length?`<details data-bot-events><summary>Recent bot commands · ${bot.events.length}</summary>${bot.events.slice().reverse().map(row=>`<p class="vv-caption">${time(row.timestamp)} · ${escape(row.route)} · ${escape(row.outcome)} (${row.http_status})<br><code>${row.id}</code></p>`).join('')}<p class="vv-caption">Command acknowledgement does not establish visible presentation. Inspect delivery activity and the output.</p></details>`:''}</section>`;
  }

  function outline(snapshot){return status(snapshot)+controlPanel(snapshot)+window.liveOutline.render(snapshot);}

  const testGate = () => '<section class="vv-panel preview-about" aria-label="Sample mode separation"><h2>Sample demo</h2><p class="vv-caption">Sample controls are separate from the detector feed. Switch to Sample demo to run them; the detector feed and its controls remain separate.</p><button type="button" class="vv-btn" data-action="sample-mode">Open sample demo</button></section>';
  function updateRecoveryAvailability(snapshot) {
    reconcileCommand(snapshot);
    const session = snapshot.session, control = session?.control;
    for(const button of document.querySelectorAll('[data-engine-action="start_bot"],[data-engine-action="stop_bot"],[data-engine-action="pull_settings"]')){
      button.disabled=snapshot.connection!=='connected'||session?.session_id!==button.dataset.engineSession||!control?.actions.includes(button.dataset.engineAction)||command?.outcome==='submitted';
    }
    for (const button of document.querySelectorAll('[data-recovery-revision]')) {
      button.disabled = snapshot.connection !== 'connected' || session?.session_id !== button.dataset.engineSession ||
        control?.state !== 'stopped' || control?.recovery?.revision !== button.dataset.recoveryRevision ||
        !control?.actions.includes(button.dataset.engineAction) || command?.outcome === 'submitted';
    }
    for(const button of document.querySelectorAll('[data-suggestion-id]')){
      button.disabled=snapshot.connection!=='connected'||session?.session_id!==button.dataset.engineSession||
        control?.state!=='running'||!control?.actions.includes('send_suggestion')||!control?.suggestions?.active||
        control.suggestions.busy||!control.suggestions.rows.some(row=>row.id===button.dataset.suggestionId&&row.state==='available')||command?.outcome==='submitted';
    }
  }
  function connectionNotice(snapshot) {
    if (!snapshot.session?.host?.managed) return 'Local engine connection. Controls require explicit opt-in in the detector.';
    if (snapshot.connection !== 'connected' || snapshot.session.control?.state === 'closed') {
      return 'Bundled backend feed unavailable. Showing the last snapshot; controls are disabled.';
    }
    return 'Bundled backend connected. Use the engine controls to start or stop.';
  }
  window.observerView = Object.freeze({ session: sessionView, activity, settings, outline, testGate, controls: controlPanel, updateRecoveryAvailability, connectionNotice });
  const root = document.getElementById('verseview-prototype');
  root.addEventListener('toggle', event => {
    if(event.target.matches('[data-suggestion-panel]')){
      const key=event.target.dataset.suggestionSession;
      if(event.target.open)suggestionsOpen=key;else if(suggestionsOpen===key)suggestionsOpen=null;
      return;
    }
    if (!event.target.matches('[data-recovery-preview]')) return;
    const key = event.target.dataset.recoveryKey;
    if (event.target.open) recoveryOpen = key;
    else if (recoveryOpen === key) recoveryOpen = null;
  }, true);
  root.addEventListener('click', async event => {
    const button = event.target.closest('[data-engine-action]');
    if (!button || button.disabled || window.previewShell.getMode() !== 'observer' || command?.outcome === 'submitted') return;
    const action = button.dataset.engineAction;
    const sessionId = button.dataset.engineSession;
    const hostId = window.previewShell.getObserver().session?.control?.id;
    command = { hostId, action, outcome: 'submitted', reason: 'Submitting to the selected detector.' };
    root.dispatchEvent(new Event('preview:observer'));
    try {
      const submitted = action === 'start' ? await window.verseviewDesktop.startEngine(sessionId)
        : action === 'stop' ? await window.verseviewDesktop.stopEngine(sessionId)
        : action === 'panic' ? await window.verseviewDesktop.clearOutput(sessionId)
        : ['start_bot','stop_bot'].includes(action) ? await window.verseviewDesktop.botControl(sessionId,action)
        : action==='pull_settings' ? await window.verseviewDesktop.pullSettings(sessionId)
        : action === 'send_suggestion' ? await window.verseviewDesktop.sendSuggestion(sessionId, button.dataset.suggestionId)
        : ['restore_session', 'discard_session'].includes(action) ? await window.verseviewDesktop.recoverSession(sessionId, button.dataset.recoveryRevision, action === 'restore_session')
        : await window.verseviewDesktop.resolveCandidate(sessionId, button.dataset.candidate, action === 'approve');
      command = { ...submitted, hostId };
      const id = command.id;
      setTimeout(() => {
        const result = window.previewShell.getObserver().session?.control?.results.find(item => item.id === id);
        if (command?.id === id && command.outcome === 'submitted') {
          command = result ? { ...result, hostId } : { ...command, outcome: 'unknown', reason: 'No acknowledgement received. Check the detector before trying again.' };
          root.dispatchEvent(new Event('preview:observer'));
        }
      }, 12000);
    } catch (error) {
      command = { hostId, action, outcome: 'failed', reason: error.message };
    }
    root.dispatchEvent(new Event('preview:observer'));
  });
  root.addEventListener('click', async event => {
    const button = event.target.closest('[data-backend-action]');
    if (!button || button.disabled || window.previewShell.getMode() !== 'observer') return;
    button.disabled = true;
    try {
      if (button.dataset.backendAction === 'launch') await window.verseviewDesktop.launchBackend();
      else if (button.dataset.backendAction === 'close') await window.verseviewDesktop.closeBackend();
      else await window.verseviewDesktop.openBackendFolder();
    } catch { /* The manager publishes status; no retry or raw error is shown. */ }
    button.disabled = false;
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && event.shiftKey && !event.repeat && window.previewShell.getMode() === 'observer') {
      const button = root.querySelector('[data-engine-action="panic"]');
      if (button && !button.disabled) { event.preventDefault(); button.click(); }
      else {
        const snapshot = window.previewShell.getObserver();
        if (snapshot.connection === 'connected' && snapshot.session?.control?.actions.includes('panic')) {
          event.preventDefault(); window.verseviewDesktop.clearOutput(snapshot.session.session_id).catch(() => {});
        }
      }
    }
  });
  root.addEventListener('change', async event => {
    if (!event.target.matches('[data-observer-source]') || !window.verseviewDesktop) return;
    try { await window.verseviewDesktop.selectObserver(event.target.value || null); } catch { /* Reader will retain its previous source. */ }
  });
})();
