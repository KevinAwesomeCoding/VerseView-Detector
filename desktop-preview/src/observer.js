(() => {
  'use strict';
  const escape = value => String(value ?? '').replace(/[&<>"']/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[character]);
  let command = null;
  let recoveryOpen = null;
  const languageNames = { en: 'English', ml: 'Malayalam', hi: 'Hindi', multi: 'Multilingual' };
  const outcomeNames = { COMMAND_ACCEPTED: 'Command accepted', SUPPRESSED: 'Suppressed',
    MANUAL_CONFIRM_REQUIRED: 'Awaiting operator approval', QUEUED: 'Queued', CANCELLED: 'Cancelled',
    EXPIRED: 'Expired', ERROR: 'Error', DELIVERY_FAILED: 'Delivery failed', DETECTED: 'Candidate detected' };
  const time = value => value ? `<time datetime="${escape(value)}" title="${escape(value)}">${escape(new Date(value).toLocaleTimeString())}</time>` : 'Not received';
  const outcome = value => outcomeNames[value] || value.replaceAll('_', ' ').toLowerCase();
  const streamName = (session, role) => role === 'unknown' ? 'Unattributed stream'
    : `${role === 'primary' ? 'Primary' : 'Secondary'} · ${languageNames[session.config.streams[role].language] || session.config.streams[role].language || 'Language not reported'}`;

  function controlPanel(snapshot) {
    const session = snapshot.session;
    const control = session?.control;
    if (!control) return '<p class="vv-caption vv-observer-note">Read-only connection. Engine controls remain in the existing detector.</p>';
    if (command?.hostId && command.hostId !== control.id) command = null;
    const enabled = snapshot.connection === 'connected';
    const result = control.results.find(item => item.id === command?.id);
    if (result) command = { ...result, hostId: control.id };
    const disabled = !enabled || command?.outcome === 'submitted';
    const commandLabels = { submitted: 'Request sent', requested: 'Request acknowledged', answered: 'Decision acknowledged', prepared: 'Recovery prepared', discarded: 'Recovery discarded', rejected: 'Request rejected', failed: 'Request failed', unknown: 'Outcome unknown' };
    const notice = command ? `${commandLabels[command.outcome] || command.outcome}. ${command.reason || 'Waiting for the detector to acknowledge.'}` : 'Start uses the existing detector settings. Approval returns to the existing delivery checks.';
    return recoveryPanel(snapshot, disabled) + `<section class="vv-panel vv-engine-control" aria-label="Detector controls"><div class="vv-panel-head"><div><h2>Detector controls</h2><p class="vv-caption">${escape(control.state)} · PID ${session.pid}</p></div><div class="vv-control-actions">${['start', 'stop', ...(control.actions.includes('panic') ? ['panic'] : [])].map(action => `<button type="button" class="vv-btn ${action === 'start' ? 'vv-btn-primary' : ''}" data-engine-action="${action}" data-engine-session="${session.session_id}" ${disabled || !control.actions.includes(action) ? 'disabled' : ''}>${action === 'start' ? 'Start engine' : action === 'panic' ? 'Clear output' : 'Stop engine'}</button>`).join('')}</div></div>
      <p class="vv-caption" role="status" aria-live="polite" data-command-status>${escape(enabled ? notice : 'Connection unavailable. Commands disabled; showing the last snapshot.')}</p>
      ${control.pending.length ? `<div class="vv-pending-list"><h3>Awaiting your decision</h3>${control.pending.map(item => `<div class="vv-pending-candidate"><div><strong>${escape(item.reference)}</strong><p class="vv-caption">${Math.round(item.confidence * 100)}% confidence · ${escape(streamName(session, item.stream))} · ${escape(item.source)}</p><code>${escape(item.candidate_id)}</code></div><div class="vv-control-actions">${['approve', 'reject'].map(action => `<button type="button" class="vv-btn ${action === 'approve' ? 'vv-btn-primary' : ''}" data-engine-action="${action}" data-engine-session="${session.session_id}" data-candidate="${escape(item.candidate_id)}" ${disabled ? 'disabled' : ''}>${action === 'approve' ? 'Approve' : 'Reject'} ${escape(item.reference)}</button>`).join('')}</div></div>`).join('')}</div>` : '<p class="vv-caption">No candidates awaiting approval.</p>'}</section>`;
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
    return `<section class="vv-backend-status" aria-label="Bundled backend status"><div><strong>${value.status === 'unavailable' ? 'External detector connection' : 'Standalone backend preview'}</strong><p class="vv-caption">${escape(value.status === 'unavailable' ? 'This build has no native companion. An updated external detector can still publish the feed.' : value.message)}${value.pid ? ` · PID ${value.pid}` : ''}</p>${session?.host?.notice ? `<p class="vv-caption">${escape(session.host.notice)}</p>` : ''}${warmupStatus(session?.host?.warmup)}</div><div class="vv-control-actions">${value.owned ? '<button type="button" class="vv-btn" data-backend-action="folder">Open backend settings folder</button><button type="button" class="vv-btn" data-backend-action="close">Close backend</button>' : value.status !== 'unavailable' ? '<button type="button" class="vv-btn" data-backend-action="launch">Launch bundled backend</button>' : ''}${busy ? '<span class="vv-caption">Please wait…</span>' : ''}</div></section>`;
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
    const lines = session?.transcripts.filter(row => row.stream === role && row.is_final).slice(-4) || [];
    const partial = session?.transcripts.filter(row => row.stream === role && !row.is_final).at(-1);
    const lastEvent = session?.delivery_events.filter(row => row.stream === role && row.reference).at(-1);
    const streamState = session?.streams[role]?.state;
    const streamStatus = config?.enabled === false ? 'Disabled in detector' : ({ configured: 'Configured',
      starting: 'Starting in detector', transcript_received: 'Transcript received', stopped: 'Stream stopped', error: 'Stream error'
    })[streamState] || 'Waiting for status';
    return `<section class="vv-panel vv-stream vv-observed-stream" data-speech-stream="${role}" aria-label="${escape(name)} observed speech">
      <div class="vv-stream-header"><div><h2 lang="${escape(language || 'und')}">${escape(label)}</h2><p class="vv-stream-provider">${role === 'primary' ? 'Primary' : 'Secondary'} · ${escape(config?.provider || 'Provider not reported')}</p></div><span class="vv-badge">${escape(streamStatus)}</span></div>
      <div class="vv-stream-results">${lines.length ? lines.map(row => `<div class="vv-transcript-line"><span class="vv-transcript-time">${time(row.timestamp)}</span><p lang="${escape(row.language || 'und')}">${escape(row.text)}</p>${row.translation && row.translation !== row.text ? `<details class="vv-caption"><summary>English translation</summary><p lang="en">${escape(row.translation)}</p></details>` : ''}</div>`).join('') : '<p class="vv-observer-empty">No final transcript received.</p>'}</div>
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
    return status(snapshot) + controlPanel(snapshot) + (layout.endsWith('focus') ? output(session) + transcripts : transcripts + output(session))
      + (unknown.length ? `<section class="vv-panel vv-observer-unknown"><h2>Unattributed speech</h2>${unknown.map(row => `<p>${escape(row.text)}</p>`).join('')}</section>` : '')
      + '<p class="vv-caption vv-observer-note">The detector owns recognition and delivery. Queue and presentation settings remain in its existing window.</p>';
  }

  function activity(snapshot) {
    const session = snapshot.session;
    return status(snapshot) + controlPanel(snapshot) + `<section class="vv-panel" aria-label="Observed delivery activity"><div class="vv-panel-head"><h2>Engine delivery events</h2><span class="vv-pill">Read only</span></div>${session?.delivery_events.length ? session.delivery_events.slice().reverse().map(event => `<div class="vv-activity-item"><span class="vv-dot"></span><div><div class="vv-activity-title">${escape(event.reference || 'No reference')} · ${escape(outcome(event.outcome))}</div><div class="vv-activity-meta">${escape(streamName(session, event.stream))} · ${escape(event.language)} · ${escape(event.source)}<br>${escape(event.candidate_id)} · ${escape(event.stage)} · ${escape(event.outcome)}</div><p class="vv-activity-why">${escape(event.reason)}</p></div><span class="vv-time">${time(event.timestamp)}</span></div>`).join('') : '<p class="vv-observer-empty">No delivery events received. Nothing here establishes visible presentation output.</p>'}</section>`;
  }

  function settings(snapshot) {
    const session = snapshot.session;
    return status(snapshot) + window.detectorSettings.render(snapshot) + `<section class="vv-panel preview-about" aria-label="Observer setup"><h2>Local detector connection</h2>
      <p class="vv-caption">${session?.host?.managed ? "This dashboard owns the bundled backend and its private preview profile. The installed detector has not been replaced." : "The preview reads structured snapshots from your local VerseView/Observer folder. The installed detector has not been replaced."}</p>
      <p class="vv-caption">An updated detector must be started with <code>VERSEVIEW_OBSERVER=1</code> to publish the feed. Also set <code>VERSEVIEW_DESKTOP_CONTROL=1</code> to enable start/stop and candidate decisions. Without that opt-in the connection stays read only. Speech and connection settings can be saved above while stopped; credentials and advanced options remain in the detector.</p>
      <p class="vv-caption">${session ? `Session ${escape(session.session_id)} · Bible setting: ${escape(session.config.bible_translation || 'not reported')}` : 'No observer session selected.'}</p></section>`;
  }

  const testGate = () => '<section class="vv-panel preview-about" aria-label="Sample mode separation"><h2>Sample demo</h2><p class="vv-caption">Sample controls are separate from the detector feed. Switch to Sample demo to run them; the detector feed and its controls remain separate.</p><button type="button" class="vv-btn" data-action="sample-mode">Open sample demo</button></section>';
  function updateRecoveryAvailability(snapshot) {
    const session = snapshot.session, control = session?.control;
    for (const button of document.querySelectorAll('[data-recovery-revision]')) {
      button.disabled = snapshot.connection !== 'connected' || session?.session_id !== button.dataset.engineSession ||
        control?.state !== 'stopped' || control?.recovery?.revision !== button.dataset.recoveryRevision ||
        !control?.actions.includes(button.dataset.engineAction) || command?.outcome === 'submitted';
    }
  }
  window.observerView = Object.freeze({ session: sessionView, activity, settings, testGate, controls: controlPanel, updateRecoveryAvailability });
  const root = document.getElementById('verseview-prototype');
  root.addEventListener('toggle', event => {
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
