(() => {
  'use strict';
  const escape = value => String(value ?? '').replace(/[&<>"']/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[character]);
  let command = null;
  let askNotice = '';
  let recoveryOpen = null;
  let suggestionsOpen = null;
  let newSessionBusy = false;
  let newSessionNotice = '';
  let suppressedSession = null;
  let dismissedSuppressed = new Set();
  const languageNames = { en: 'English', ml: 'Malayalam', hi: 'Hindi', multi: 'Multilingual' };
  const outcomeNames = { COMMAND_ACCEPTED: 'Command accepted', SUPPRESSED: 'Suppressed',
    MANUAL_CONFIRM_REQUIRED: 'Awaiting operator approval', QUEUED: 'Queued', CANCELLED: 'Cancelled',
    EXPIRED: 'Expired', ERROR: 'Error', DELIVERY_FAILED: 'Delivery failed', DETECTED: 'Candidate detected' };
  const time = value => value ? `<time datetime="${escape(value)}" title="${escape(value)}">${escape(new Date(value).toLocaleTimeString())}</time>` : 'Not received';
  const outcome = value => outcomeNames[value] || value.replaceAll('_', ' ').toLowerCase();
  const streamName = (session, role) => role === 'unknown' ? 'Unattributed stream'
    : `${role === 'primary' ? 'Primary' : 'Secondary'} · ${languageNames[session.config.streams[role].language] || session.config.streams[role].language || 'Language not reported'}`;

  const developer=()=>window.previewShell.isDeveloper?.()===true;
  function friendly(event){
    if(!event)return 'Waiting for a reference';
    const names={COMMAND_ACCEPTED:'Command sent',MANUAL_CONFIRM_REQUIRED:'Needs approval',QUEUED:'Waiting for the verse reading',DETECTED:'Reference detected',CANCELLED:'Cancelled',EXPIRED:'Expired',ERROR:'Could not process reference',DELIVERY_FAILED:'Could not send',SUPPRESSED:/duplicate|already.*sent|already.*accepted|cooldown/i.test(event.reason||'')?'Already sent recently':'Suppressed · not sent'};
    return names[event.outcome]||outcome(event.outcome);
  }
  function remoteMessage(value){
    if(!value)return '';
    const failure={browser:'The browser or its driver could not start.',remote:'The remote page could not be reached.',controls:'The page did not provide the required VerseVIEW controls.'}[value.reason]||'';
    return {connecting:`Connecting to VerseVIEW · attempt ${value.attempt}/5…`,
      retrying:`Attempt ${value.attempt}/5 failed. ${failure} Retrying in 5 seconds…`,
      connected:`VerseVIEW connected on attempt ${value.attempt}/5.`,
      failed:`Could not connect to VerseVIEW after 5 attempts. ${failure} Check that VerseVIEW and its remote are enabled, review the control URL in Settings, then try again.`,
      cancelled:'VerseVIEW connection cancelled. Listening is stopped.'}[value.status]||'';
  }
  function remoteStatus(snapshot){
    const session=snapshot.session,value=session?.remote_connection;
    if(!value)return session?.engine_state==='connection_failed'?'<p role="status">Could not connect to VerseVIEW. Review the remote URL in Settings, then try again.</p>':'';
    return `<section class="vv-remote-status" aria-label="VerseVIEW connection"><p role="status" aria-live="polite">${escape(remoteMessage(value))}${snapshot.connection!=='connected'?' Last reported status; the backend connection is unavailable.':''}</p><details data-connection-history data-connection-session="${escape(session.session_id)}"><summary>Connection activity</summary><ol>${(session.connection_events||[]).map(row=>`<li>${time(row.timestamp)} · ${escape(remoteMessage(row))}</li>`).join('')}</ol></details></section>`;
  }
  function compactControls(snapshot){
    reconcileCommand(snapshot);
    const s=snapshot.session,c=s?.control,backend=window.previewShell.getBackend();
    if(!newSessionBusy&&c?.state==='running')newSessionNotice='';
    const flow=window.consumerFlow?.state()||{},connected=snapshot.connection==='connected';
    const running=['running','starting','stopping'].includes(c?.state),error=Object.values(s?.streams||{}).some(v=>v.state==='error');
    const label=flow.busy?'Preparing…':!connected&&backend.owned?'Connection unavailable':s?.remote_connection?.status==='failed'&&c?.state==='stopped'?'Connection failed':c?.operator?.emergency?c.operator.busy?'Stopping & saving…':'Stopped':error?'Needs attention':running?c.state==='running'?'Listening':c.state==='stopping'?'Stopping…':'Starting…':connected?'Ready':'Stopped';
    const disabled=flow.busy||newSessionBusy||command?.outcome==='submitted';
    const canNew=connected&&window.verseviewDesktop&&(c?.state==='running'?c.actions.includes('stop'):c?.state==='stopped'&&c.actions.includes('new_session'));
    const listening=running?`<button class="vv-btn vv-btn-primary" type="button" data-live-stop ${!connected||!c.actions.includes('stop')||newSessionBusy?'disabled':''}>Stop listening</button>`
      :`<button class="vv-btn vv-btn-primary" type="button" data-consumer-prepare="start" ${disabled||!window.verseviewDesktop?'disabled':''}>${s?.remote_connection?.status==='failed'&&c?.state==='stopped'?'Retry connection':'Start listening'}</button>`;
    const ask=c?.actions.includes('set_ask_before_sending')?`<button class="vv-btn vv-ask-toggle" type="button" data-ask-before-send aria-pressed="${c.ask_before_sending===true}" ${!connected?'disabled':''}>Ask before sending <strong>${c.ask_before_sending?'On':'Off'}</strong></button>`:'';
    const emergency=window.operatorTools?.safety(snapshot,false)||'';
    const more=`<details class="vv-control-menu" data-control-menu><summary class="vv-btn">More actions</summary><div class="vv-control-menu-items" role="group" aria-label="More listening actions"><button class="vv-btn" type="button" data-new-session ${disabled||!canNew?'disabled':''}>${newSessionBusy?'Preparing new session…':'New session'}</button>${c?.actions.includes('panic')?`<button class="vv-btn" type="button" data-engine-action="panic" data-engine-session="${s.session_id}" ${!connected?'disabled':''}>Clear output</button>`:''}<div class="vv-control-menu-secondary">${window.operatorTools?.header(snapshot)||''}</div></div></details>`;
    return `<div class="vv-consumer-status" aria-label="Listening controls"><span class="vv-badge ${running&&!error?'vv-ok':''}"><span class="vv-dot"></span>${label}</span><div class="vv-control-actions">${listening}${flow.busy?'<button class="vv-btn" type="button" data-consumer-cancel>Cancel preparation</button>':''}${ask}${emergency}${more}</div></div>${window.operatorTools?.recoveryNotice(snapshot)||''}${window.operatorTools?.render(snapshot)||''}${remoteStatus(snapshot)}${window.sessionSetup?.banner(snapshot)||''}`;
  }
  function consumerNotice(snapshot){
    const c=snapshot.session?.control,flow=window.consumerFlow?.state();
    if(askNotice)return askNotice;
    if(newSessionNotice)return newSessionNotice;
    if(flow?.busy)return flow.notice;
    if(snapshot.connection!=='connected'&&window.previewShell.getBackend().owned)return 'Connection lost. Listening status is unknown; reconnect before sending commands.';
    if(c?.operator?.emergency||c?.operator?.status==='failed')return c.operator.message;
    if(c?.state==='stopped'&&c?.operator?.message)return c.operator.message;
    if(c?.sync&&['pulling','failed','conflict'].includes(c.sync.status))return c.sync.message;
    const error=Object.entries(snapshot.session?.streams||{}).find(([,v])=>v.state==='error');
    if(error)return `${streamName(snapshot.session,error[0])}: speech recognition needs attention. Check the provider connection and allowance in Settings.`;
    if(command&&['failed','rejected','unknown'].includes(command.outcome))return command.reason||'The request needs attention. Check History.';
    if(command?.outcome==='submitted'&&['approve','reject'].includes(command.action))return 'Sending your decision to the detector…';
    return c?.state==='running'?'':flow?.notice||'';
  }
  function consumerDecisions(snapshot){
    const s=snapshot.session,c=s?.control;if(!c)return '<section class="vv-engine-control"></section>';
    reconcileCommand(snapshot);const disabled=snapshot.connection!=='connected'||command?.outcome==='submitted';
    return `<section class="vv-engine-control" aria-label="Reference decisions">${c.operator?'':recoveryPanel(snapshot,disabled)}${c.pending.length?`<section class="vv-panel vv-consumer-decisions"><h2>Needs your approval</h2>${c.pending.map(item=>`<div class="vv-pending-candidate"><div><strong>${escape(item.reference)}</strong><p class="vv-caption">${Math.round(item.confidence*100)}% confidence · ${escape(languageNames[item.language]||streamName(s,item.stream))}</p></div><div class="vv-control-actions">${['approve','reject'].map(a=>`<button class="vv-btn ${a==='approve'?'vv-btn-primary':''}" type="button" data-engine-action="${a}" data-engine-session="${s.session_id}" data-candidate="${escape(item.candidate_id)}" ${disabled?'disabled':''}>${a==='approve'?'Approve':'Dismiss'} ${escape(item.reference)}</button>`).join('')}</div></div>`).join('')}</section>`:''}${suggestionPanel(snapshot,disabled)}</section>`;
  }
  function consumerOutput(session){
    const latest=session?.delivery_events.filter(e=>e.reference).at(-1);
    const sent=session?.delivery_events.filter(e=>e.outcome==='COMMAND_ACCEPTED').at(-1);
    return `<section class="vv-panel vv-output" aria-label="Reference result"><div class="vv-output-top"><span class="vv-eyebrow">${latest?latest.outcome==='SUPPRESSED'?'Reference suppressed':'Reference detected':'Ready when you are'}</span>${latest?`<span class="vv-badge">${escape(friendly(latest))}</span>`:''}</div><div class="vv-output-ref">${escape(latest?.reference||'No reference yet')}</div><p class="vv-caption vv-observer-output-note">${latest?.outcome==='SUPPRESSED'?escape('Not sent. '+(latest.reason||'The reference did not pass the delivery checks.')):latest?.outcome==='COMMAND_ACCEPTED'?'VerseVIEW accepted the command. Check its presentation screen for the displayed verse.':latest?'Follow the reference status here as speech continues.':'Spoken references and their delivery status will appear here.'}</p>${sent?`<div class="vv-output-foot"><span>Last sent: ${escape(sent.reference)}</span>${time(sent.timestamp)}</div>`:''}</section>`;
  }
  function suppressedReview(snapshot){
    const session=snapshot.session;
    if(!session)return '';
    if(suppressedSession!==session.session_id){suppressedSession=session.session_id;dismissedSuppressed=new Set();}
    const events=session.delivery_events||[];
    const latest=[...events].reverse().find(e=>e.outcome==='SUPPRESSED'&&e.reference&&!dismissedSuppressed.has(e.reference));
    if(!latest)return '';
    const later=events.slice(events.lastIndexOf(latest)+1);
    if(later.some(e=>e.outcome==='COMMAND_ACCEPTED'&&e.reference===latest.reference))return '';
    const available=snapshot.connection==='connected'&&session.control?.actions.includes('verse_preview');
    return `<section class="vv-panel vv-suppressed-review" aria-label="Detected reference awaiting review"><div><strong>Detected ${escape(latest.reference)}</strong><p class="vv-caption">It was not displayed. ${escape(latest.reason||'It did not pass the delivery checks.')} Review the verse if this is what you meant.</p></div><div class="vv-control-actions"><button type="button" class="vv-btn vv-btn-primary" data-suppressed-review="${escape(latest.reference)}" ${available?'':'disabled'}>Review verse</button><button type="button" class="vv-btn" data-suppressed-dismiss="${escape(latest.reference)}">Dismiss</button></div></section>`;
  }
  function history(snapshot){
    const rows=new Map();for(const e of snapshot.session?.delivery_events||[])if(e.reference)rows.set(e.candidate_id,e);
    return `<section class="vv-panel" aria-label="Reference history"><div class="vv-panel-head"><h2>Recent references</h2></div>${rows.size?[...rows.values()].reverse().map(e=>`<div class="vv-history-row"><div><strong>${escape(e.reference)}</strong><p class="vv-caption">${escape(friendly(e))} · ${escape(streamName(snapshot.session,e.stream))}</p>${e.outcome==='COMMAND_ACCEPTED'&&e.trigger_text?`<button type="button" class="vv-trigger-link" data-show-transcript="${escape(e.transcript_id)}" data-trigger-stream="${escape(e.stream)}" title="Show this speech in the full transcript">“${escape(e.trigger_text)}” <span aria-hidden="true">↗</span></button>`:e.outcome==='COMMAND_ACCEPTED'?'<p class="vv-caption">Triggering speech was not captured for this reference.</p>':''}</div>${time(e.timestamp)}</div>`).join(''):'<p class="vv-observer-empty">References will appear here as you listen.</p>'}</section>`;
  }

  function reconcileCommand(snapshot){
    const control=snapshot.session?.control;
    if(command?.hostId&&control&&command.hostId!==control.id)command=null;
    const result=control?.results.find(item=>item.id===command?.id);
    if(result)command={...result,hostId:control.id};
  }

  function controlPanel(snapshot) {
    if(!developer())return consumerDecisions(snapshot);
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
    if(!value)return '';
    const phase={off:'Off',stopped:'Stopped',waiting:'Waiting for speech',scanning:'Scanning speech',suggested:'Suggestion ready',configuration_required:'Provider setup required',rate_limited:'Rate limited',budget_limited:'Free usage limit reached',failed:'No usable response · check provider status'};
    const stateLabel={sending:'Send in progress',accepted:'Command accepted · visible output unverified',review:'No acceptance confirmed · inspect delivery activity',unknown:'Outcome unknown after Stop · inspect delivery activity'};
    const locked=(action,row)=>disabled||!control.actions.includes(action)||(row&&row.state!=='available');
    return `<details class="vv-panel vv-suggestions" data-suggestion-panel data-suggestion-session="${session.session_id}" ${suggestionsOpen===session.session_id?'open':''}><summary>Verse suggestions · ${escape(phase[value.phase]||'Waiting')} · ${value.rows.length}</summary><div class="vv-suggestions-body"><p class="vv-caption" role="status">${escape(phase[value.phase]||'Waiting')}. Enable or configure the watcher in Settings. Every suggestion needs your explicit Display action. Advice expires after 90 seconds.</p>${developer()?`<p class="vv-caption">Effective route: ${escape(value.effective_route||'Not configured')} · ${value.cycles} cycles · ${value.suggested} suggestions · ${value.discarded} discarded</p>`:''}
      ${value.rows.length?`<button type="button" class="vv-btn" data-engine-action="clear_suggestions" data-engine-session="${session.session_id}" data-suggestion-revision="${escape(value.revision)}" ${locked('clear_suggestions')?'disabled':''}>Clear suggestions</button>`:''}
      ${value.rows.length?value.rows.slice().reverse().map(row=>`<div class="vv-pending-candidate"><div><strong>${escape(row.reference)}</strong><p class="vv-caption">${escape(languageNames[row.language]||streamName(session,row.stream))} · ${escape(streamName(session,row.stream))} · ${Math.round(row.confidence*100)}% · ${time(row.created_at)}</p><p class="vv-caption">${escape(row.state==='available'?'Awaiting your choice':stateLabel[row.state])}</p>${row.reasoning?`<p class="vv-caption">${escape(row.reasoning)}</p>`:''}${row.message?`<p class="vv-caption">${escape(row.message)}</p>`:''}${developer()&&row.candidate_id?`<code>${escape(row.candidate_id)}</code>`:''}</div><div class="vv-control-actions"><button type="button" class="vv-btn" data-suggestion-preview="${row.id}" ${locked('preview_suggestion',row)?'disabled':''}>Preview ${escape(row.reference)}</button><button type="button" class="vv-btn" data-engine-action="send_suggestion" data-engine-session="${session.session_id}" data-suggestion-id="${row.id}" ${locked('send_suggestion',row)||!value.active||value.busy?'disabled':''}>Display ${escape(row.reference)}</button><button type="button" class="vv-btn" data-engine-action="dismiss_suggestion" data-engine-session="${session.session_id}" data-review-suggestion="${row.id}" ${locked('dismiss_suggestion',row)?'disabled':''}>Dismiss ${escape(row.reference)}</button></div></div>`).join(''):'<p class="vv-caption">No current suggestions.</p>'}</div></details>`;
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
      <div class="vv-control-actions">${['restore_session', 'discard_session'].filter(action => value.status !== 'invalid' || action === 'discard_session').map(action => `<button type="button" class="vv-btn ${action === 'restore_session' ? 'vv-btn-primary' : ''}" data-engine-action="${action}" data-engine-session="${session.session_id}" data-recovery-revision="${escape(value.revision)}" ${disabled || !control.actions.includes(action) ? 'disabled' : ''}>${developer()?(action === 'restore_session' ? 'Restore saved session' : 'Discard saved session'):(action === 'restore_session' ? 'Resume saved session' : 'Start new')}</button>`).join('')}</div></div></section>`;
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
    const active = [...(session?.delivery_events||[])].reverse().find(row => row.outcome === 'COMMAND_ACCEPTED');
    const streamState = session?.streams[role]?.state;
    const streamStatus = config?.enabled === false ? 'Disabled in detector' : ({ configured: 'Configured',
      starting: 'Starting in detector', transcript_received: 'Transcript received', stopped: 'Stream stopped', error: 'Speech stream ended — check microphone or provider'
    })[streamState] || 'Waiting for status';
    return `<section class="vv-panel vv-stream vv-observed-stream" data-speech-stream="${role}" aria-label="${escape(name)} observed speech">
      <div class="vv-stream-header"><div><h2 lang="${escape(language || 'und')}">${escape(label)}</h2><p class="vv-stream-provider">${role === 'primary' ? 'Primary' : 'Secondary'} · ${escape(config?.provider || 'Provider not reported')}</p></div><span class="vv-badge">${escape(streamStatus)}</span></div>
      <div class="vv-stream-results ${full ? 'vv-full-transcript' : ''}" ${full ? `data-full-transcript="${role}" tabindex="0" aria-label="${escape(name)} full transcript"` : ''}>${lines.length ? lines.map(row => `<div class="vv-transcript-line ${row.id===active?.transcript_id?'vv-transcript-trigger':''}" data-transcript-id="${escape(row.id)}"><span class="vv-transcript-time">${time(row.timestamp)}</span><p lang="${escape(window.sessionPolicy?.transcript(row,session?.control?.settings?.values?.desktop_transcript_display||'original').language||row.language||'und')}">${row.id===active?.transcript_id?`<mark>${escape(window.sessionPolicy?.transcript(row,session?.control?.settings?.values?.desktop_transcript_display||'original').text||row.text)}</mark>`:escape(window.sessionPolicy?.transcript(row,session?.control?.settings?.values?.desktop_transcript_display||'original').text||row.text)}</p><span class="vv-caption">${escape(window.sessionPolicy?.transcript(row,session?.control?.settings?.values?.desktop_transcript_display||'original').label||'Provider transcription')}${row.id===active?.transcript_id?` · Triggered ${escape(active.reference)}`:''}</span>${session?.control?.settings?.values?.desktop_transcript_display==='translation'&&row.translation?`<details class="vv-caption"><summary>Provider text${row.text_kind==='transliteration'?' (transliteration)':''}</summary><p>${escape(row.text)}</p></details>`:''}${row.translation && row.translation !== row.text && session?.control?.settings?.values?.desktop_transcript_display!=='translation' ? `<details class="vv-caption"><summary>English translation</summary><p lang="en">${escape(row.translation)}</p></details>` : ''}</div>`).join('') : '<p class="vv-observer-empty">No final transcript received.</p>'}</div>
      ${partial ? `<div class="vv-partial"><span class="vv-caption">${partial.text_kind==='transliteration'?'Interim provider transliteration':'Interim provider transcription'}</span><p lang="${escape(partial.language || 'und')}">${escape(partial.text)}</p></div>` : ''}
      ${!lastEvent&&!developer()?'':`<div class="vv-ref-notice">${lastEvent ? `<span><span class="vv-ref-notice-label">${developer()?'Latest reported candidate outcome':lastEvent.outcome==='SUPPRESSED'?'Reference suppressed':'Reference detected'}</span><span class="vv-ref-notice-ref">${escape(lastEvent.reference)}</span></span><span class="vv-badge">${escape(developer()?outcome(lastEvent.outcome):friendly(lastEvent))}</span>` : '<span class="vv-caption">No reference outcome reported for this stream.</span>'}</div>`}
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
    const roles=!developer()&&session?.config.streams.secondary.enabled===false?['primary']:['primary','secondary'];
    const transcripts = `<section class="vv-stream-section" aria-label="Observed speech streams"><div class="vv-dual-grid ${roles.length===1?'vv-single-stream':''}">${roles.map(role=>streamPanel(session,role)).join('')}</div></section>`;
    const unknown = session?.transcripts.filter(row => row.stream === 'unknown').slice(-3) || [];
    if(!developer())return (window.transcriptView?.isFull()?'':consumerOutput(session)+suppressedReview(snapshot))+(window.transcriptView?.controls(session)||'')+transcripts+(window.verseTools?.live(snapshot)||'')+controlPanel(snapshot)+window.detectorSettings.render(snapshot,'speech')+(window.connectionTools?.live(snapshot)||'');
    return (window.transcriptView?.isFull()?'':output(session))+(window.transcriptView?.controls(session)||'')+transcripts+(window.verseTools?.live(snapshot)||'')+controlPanel(snapshot)+window.detectorSettings.render(snapshot,'speech')+(window.connectionTools?.live(snapshot)||'')+status(snapshot)
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
    if(!developer())return `<button type="button" class="vv-btn" data-consumer-prepare="settings" ${window.consumerFlow?.state().busy?'disabled':''}>${session?.host?.managed?'Connection ready':'Prepare settings'}</button>`+window.detectorSettings.render(snapshot,'settings')+(window.connectionTools?.panel(snapshot)||'')+`<details class="vv-panel vv-connections"><summary>Connections</summary>${window.cloudSettings.render(snapshot,false)}${syncPanel(snapshot)}</details>`;
    return status(snapshot) +(window.connectionTools?.panel(snapshot)||'')+ window.cloudSettings.render(snapshot) + syncPanel(snapshot) + botPanel(snapshot) + window.detectorSettings.render(snapshot) + `<section class="vv-panel preview-about" aria-label="Observer setup"><h2>Local detector connection</h2>
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
      <p class="vv-caption">${escape(bot.message)}${developer()&&bot.pid?` · Owned PID ${bot.pid}`:''}</p>
      ${['start_bot','stop_bot'].includes(command?.action)?`<p class="vv-caption" role="status">${escape(command.reason||'Waiting for the detector to acknowledge.')}</p>`:''}
      <p class="vv-caption">${bot.configured?'Private credentials configured.':'Add discord_bot_token to the private backend settings file.'} Start connects Discord; stopping the bot leaves recognition running. Commands control this preview’s backend.</p>
      <div class="vv-control-actions">${['start_bot','stop_bot'].map(action=>`<button type="button" class="vv-btn" data-engine-action="${action}" data-engine-session="${session.session_id}" ${disabled||!control.actions.includes(action)?'disabled':''}>${action==='start_bot'?'Start bot':'Stop bot'}</button>`).join('')}</div>
      ${developer()&&bot.events.length?`<details data-bot-events><summary>Recent bot commands · ${bot.events.length}</summary>${bot.events.slice().reverse().map(row=>`<p class="vv-caption">${time(row.timestamp)} · ${escape(row.route)} · ${escape(row.outcome)} (${row.http_status})<br><code>${row.id}</code></p>`).join('')}<p class="vv-caption">Command acknowledgement does not establish visible presentation. Inspect delivery activity and the output.</p></details>`:''}</section>`;
  }

  function outline(snapshot){return (developer()?status(snapshot):'')+controlPanel(snapshot)+window.liveOutline.render(snapshot);}

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
    for(const button of document.querySelectorAll('[data-suggestion-preview],[data-review-suggestion],[data-suggestion-revision]')){
      const action=button.dataset.suggestionPreview?'preview_suggestion':button.dataset.reviewSuggestion?'dismiss_suggestion':'clear_suggestions';
      const identity=button.dataset.suggestionPreview||button.dataset.reviewSuggestion;
      button.disabled=snapshot.connection!=='connected'||!control?.actions.includes(action)||command?.outcome==='submitted'||(identity&&!control?.suggestions?.rows.some(r=>r.id===identity&&r.state==='available'));
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
  window.observerView = Object.freeze({ compactControls, consumerNotice, history, recovery:recoveryPanel,
    runtime: snapshot=>remoteStatus(snapshot)+status(snapshot)+controlPanel(snapshot)+botPanel(snapshot),
    cloud: snapshot=>window.cloudSettings.render(snapshot,true)+syncPanel(snapshot),
    start: snapshot=>submitAction({disabled:false,dataset:{engineAction:'start',engineSession:snapshot.session.session_id}}),
    session: sessionView, activity, settings, outline, testGate, controls: controlPanel, updateRecoveryAvailability, connectionNotice });
  const root = document.getElementById('verseview-prototype');
  let approvalDialog, shownCandidate, approvalBusy=false;
  function reviewContext(item){
    const context=item.context||{},spoken=String(context.detected||'').trim();
    if(!spoken)return '<p class="vv-caption">Recent speech context is unavailable for this reference.</p>';
    const index=spoken.toLowerCase().indexOf(item.reference.toLowerCase());
    const detected=index<0?`<mark>${escape(spoken)}</mark>`:
      `${escape(spoken.slice(0,index))}<mark>${escape(spoken.slice(index,index+item.reference.length))}</mark>${escape(spoken.slice(index+item.reference.length))}`;
    return `<div class="vv-approval-context">${context.before?`<p>${escape(context.before)}</p>`:''}<p>${detected}</p>${context.after?`<p>${escape(context.after)}</p>`:''}</div><p class="vv-caption">Highlighted speech led to ${escape(item.reference)}. Automatic transcription may be imperfect.</p>`;
  }
  function syncApproval(){
    const snapshot=window.previewShell.getObserver(),control=snapshot.session?.control;
    const item=control?.ask_before_sending&&control.pending?.[0];
    if(!item||snapshot.connection!=='connected'){
      if(approvalDialog?.open)approvalDialog.close();
      shownCandidate=null;return;
    }
    if(shownCandidate===item.candidate_id)return;
    shownCandidate=item.candidate_id;
    if(!approvalDialog){
      approvalDialog=document.createElement('dialog');approvalDialog.className='vv-memory-dialog vv-approval-dialog';
      approvalDialog.setAttribute('aria-labelledby','vv-approval-title');
      root.append(approvalDialog);
      approvalDialog.addEventListener('click',async event=>{
        const decision=event.target.closest('[data-approval-decision]');
        if(!decision||approvalBusy)return;
        approvalBusy=true;
        try{
          const session=window.previewShell.getObserver().session;
          const submitted=await window.verseviewDesktop.resolveCandidate(session.session_id,decision.dataset.candidate,decision.dataset.approvalDecision==='approve');
          command={...submitted,hostId:session.control.id};
          const id=submitted.id;
          setTimeout(()=>{
            if(command?.id===id&&command.outcome==='submitted'){
              command={...command,outcome:'unknown',reason:'No decision acknowledgement received. Check the reference in History before trying again.'};
              root.dispatchEvent(new Event('preview:observer'));
            }
          },12000);
          approvalDialog.close();root.dispatchEvent(new Event('preview:observer'));
        }
        catch(error){approvalDialog.querySelector('[role="status"]').textContent=error.message||'Could not send the decision. Check the connection and try again.';}
        finally{approvalBusy=false;}
      });
    }
    approvalDialog.innerHTML=`<h2 id="vv-approval-title" tabindex="-1">Display ${escape(item.reference)}?</h2><p class="vv-caption">Review what was heard before sending this verse to VerseVIEW.</p>${reviewContext(item)}<p role="status" class="vv-caption"></p><div class="vv-control-actions"><button class="vv-btn vv-btn-primary" data-approval-decision="approve" data-candidate="${escape(item.candidate_id)}">Approve and display</button><button class="vv-btn" data-approval-decision="reject" data-candidate="${escape(item.candidate_id)}">Deny</button></div>`;
    if(!approvalDialog.open){approvalDialog.showModal();approvalDialog.querySelector('#vv-approval-title')?.focus();}
  }
  root.addEventListener('preview:observer',syncApproval);
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
  async function submitAction(button) {
    if (!button || button.disabled || (command?.outcome === 'submitted'&&!['stop','panic'].includes(button.dataset.engineAction))) return;
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
        : ['dismiss_suggestion','clear_suggestions'].includes(action) ? await window.verseviewDesktop.operator(sessionId,action,action==='dismiss_suggestion'?{suggestion_id:button.dataset.reviewSuggestion}:{revision:button.dataset.suggestionRevision})
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
  }
  function waitForSession(check, timeout=60000){
    return new Promise((resolve,reject)=>{
      const deadline=Date.now()+timeout;
      const poll=()=>{
        const snapshot=window.previewShell.getObserver();
        if(snapshot.connection!=='connected')return reject(new Error('Detector connection was lost. Check the saved session before trying again.'));
        try{const value=check(snapshot);if(value)return resolve(value);}catch(error){return reject(error);}
        if(Date.now()>=deadline)return reject(new Error('The new session could not be confirmed. Check Saved sessions before trying again.'));
        setTimeout(poll,250);
      };
      poll();
    });
  }
  async function startNewSession(){
    if(newSessionBusy)return;
    const initial=window.previewShell.getObserver(),sessionId=initial.session?.session_id,control=initial.session?.control;
    if(initial.connection!=='connected'||!sessionId||!['running','stopped'].includes(control?.state))return;
    newSessionBusy=true;newSessionNotice=control.state==='running'?'Stopping and saving the current session…':'Saving the current session…';
    root.dispatchEvent(new Event('preview:observer'));
    try{
      if(control.state==='running'){
        const stopped=await window.verseviewDesktop.stopEngine(sessionId);
        await waitForSession(s=>{
          if(s.session?.session_id!==sessionId)throw new Error('The detector session changed. Check Saved sessions before trying again.');
          const result=s.session.control?.results.find(row=>row.id===stopped.id);
          if(result&&result.outcome!=='requested')throw new Error(result.reason);
          return result&&s.session.control.state==='stopped'&&s.session.control.actions.includes('new_session');
        });
      }
      const ready=window.previewShell.getObserver();
      if(ready.session?.session_id!==sessionId||!ready.session?.control?.actions.includes('new_session'))throw new Error('Wait for session saving to finish, then try New session again.');
      newSessionNotice='Preparing a blank session…';root.dispatchEvent(new Event('preview:observer'));
      const submitted=await window.verseviewDesktop.operator(sessionId,'new_session',{});
      await waitForSession(s=>{
        if(s.session?.session_id!==sessionId)return true;
        const result=s.session?.control?.results.find(row=>row.id===submitted.id);
        if(result&&result.outcome!=='requested')throw new Error(result.reason);
        return result&&s.session.control.recovery?.status==='none';
      });
      newSessionNotice='New session ready. Press Start listening.';
    }catch(error){newSessionNotice=error.message;}
    finally{newSessionBusy=false;root.dispatchEvent(new Event('preview:observer'));}
  }
  root.addEventListener('click',async event=>{
    if(event.target.closest('[data-new-session]')){await startNewSession();return;}
    if(event.target.closest('[data-live-stop]')){
      const s=window.previewShell.getObserver();
      if(s.connection==='connected'&&s.session?.control?.actions.includes('stop'))await submitAction({dataset:{engineAction:'stop',engineSession:s.session.session_id}});
      return;
    }
    if(window.previewShell.getMode()==='observer')await submitAction(event.target.closest('[data-engine-action]'));
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
  root.addEventListener('click',event=>{const button=event.target.closest('[data-suggestion-preview]');if(button&&!button.disabled)window.verseTools.previewSuggestion(button,button.dataset.suggestionPreview);});
  root.addEventListener('click',event=>{
    const button=event.target.closest('[data-suppressed-review],[data-suppressed-dismiss]');
    if(!button||button.disabled)return;
    const reference=button.dataset.suppressedReview||button.dataset.suppressedDismiss;
    const snapshot=window.previewShell.getObserver();
    if(!snapshot.session?.delivery_events.some(e=>e.outcome==='SUPPRESSED'&&e.reference===reference))return;
    if(button.dataset.suppressedDismiss){dismissedSuppressed.add(reference);root.dispatchEvent(new Event('preview:observer'));}
    else window.verseTools.previewDetected(button,reference);
  });
  root.addEventListener('change', async event => {
    if (!event.target.matches('[data-observer-source]') || !window.verseviewDesktop) return;
    try { await window.verseviewDesktop.selectObserver(event.target.value || null); } catch { /* Reader will retain its previous source. */ }
  });
  root.addEventListener('click',async event=>{
    const button=event.target.closest('[data-ask-before-send]');if(!button)return;
    const snapshot=window.previewShell.getObserver(),control=snapshot.session?.control;
    if(!control?.actions.includes('set_ask_before_sending'))return;
    button.disabled=true;
    try{await window.verseviewDesktop.operator(snapshot.session.session_id,'set_ask_before_sending',{enabled:!control.ask_before_sending});askNotice='';}
    catch(error){askNotice=error?.message||'Could not change Ask before sending. Try again.';button.disabled=false;root.dispatchEvent(new Event('preview:observer'));}
  });
})();
