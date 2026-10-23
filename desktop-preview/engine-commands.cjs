'use strict';
const fs = require('node:fs');
const path = require('node:path');
const settingsPolicy = require('./src/settings-policy.js');
const { randomUUID } = require('node:crypto');

// Only the main process writes commands. No renderer paths, URLs, or arbitrary IPC.
class EngineCommands {
  constructor(reader, { clock = Date.now } = {}) { this.reader = reader; this.clock = clock; }
  async submit(sessionId, action, candidateId, settingsChange, recoveryRevision, suggestionId, outlineChange, operatorChange) {
    if (!['set_ask_before_sending', 'start', 'stop', 'approve', 'reject', 'save_settings', 'panic', 'restore_session', 'discard_session', 'send_suggestion', 'edit_outline', 'start_bot', 'stop_bot', 'pull_settings', 'list_sessions', 'preview_session', 'resume_saved', 'save_session', 'set_worship', 'emergency_save', 'set_context', 'verse_preview', 'chapter_browse', 'send_reference', 'preview_suggestion', 'dismiss_suggestion', 'clear_suggestions', 'clear_history', 'grid_preview', 'connection_action', 'generate_notes', 'cancel_notes', 'prepare_export', 'prepare_memory_clear', 'clear_memory', 'new_session'].includes(action) || !/^[a-f0-9]{32}$/.test(sessionId || '')) {
      throw new Error('Invalid detector command');
    }
    if (['approve', 'reject'].includes(action) && (typeof candidateId !== 'string' || !candidateId || candidateId.length > 128)) {
      throw new Error('Invalid candidate');
    }
    let changes;
    const recoveryAction = ['restore_session', 'discard_session'].includes(action);
    if (recoveryAction && !/^[a-f0-9]{32}$/.test(recoveryRevision || '')) throw new Error('Invalid recovery revision');
    if (action === 'send_suggestion' && !/^[a-f0-9]{32}$/.test(suggestionId || '')) throw new Error('Invalid suggestion identity');
    if(action==='edit_outline'&&(!/^[a-f0-9]{32}$/.test(outlineChange?.revision||'')||typeof outlineChange.text!=='string'
      ||outlineChange.text.length>4000||outlineChange.text.includes('\0')))throw new Error('Invalid outline update');
    if (action === 'save_settings') {
      if (!/^[a-f0-9]{32}$/.test(settingsChange?.revision || '')) throw new Error('Invalid settings revision');
      changes = settingsPolicy.validatePatch(settingsChange.changes);
    }
    const operatorActions=['list_sessions','preview_session','resume_saved','save_session','set_worship','set_ask_before_sending','emergency_save','new_session'];
    let operatorPayload={};
    if(operatorActions.includes(action)){
      const value=operatorChange||{};
      const allowed=action==='list_sessions'?['page']:action==='preview_session'?['record_id','page']:action==='resume_saved'?['record_id','record_revision']:['set_worship','set_ask_before_sending'].includes(action)?['enabled']:[];
      if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).some(k=>!allowed.includes(k)))throw new Error('Invalid operator request');
      if(['preview_session','resume_saved'].includes(action)&&!/^[a-f0-9]{32}$/.test(value.record_id||''))throw new Error('Invalid saved-session identity');
      if(action==='resume_saved'&&!/^[a-f0-9]{32}$/.test(value.record_revision||''))throw new Error('Preview this session before resuming');
      if(['set_worship','set_ask_before_sending'].includes(action)&&typeof value.enabled!=='boolean')throw new Error('Invalid toggle choice');
      if(['list_sessions','preview_session'].includes(action)&&(!Number.isInteger(value.page)||value.page<0||value.page>(action==='list_sessions'?499:8388608)))throw new Error('Invalid session page');
      operatorPayload=value;
    }
    const verseActions=['set_context','verse_preview','chapter_browse','send_reference','grid_preview'];
    if(verseActions.includes(action)){
      const v=operatorChange||{};
      const keys=['set_context','grid_preview'].includes(action)?['reference','context_revision']:action==='send_reference'?['selection_id']:action==='chapter_browse'?['reference','page']:['reference'];
      if(!v||typeof v!=='object'||Array.isArray(v)||Object.keys(v).some(k=>!keys.includes(k)))throw new Error('Invalid verse tool request');
      if(action!=='send_reference'&&(typeof v.reference!=='string'||!v.reference.trim()||v.reference.length>128||v.reference.includes('\0')))throw new Error('Enter a bounded Bible reference');
      if(['set_context','grid_preview'].includes(action)&&!/^[a-f0-9]{32}$/.test(v.context_revision||''))throw new Error('Reload the current context');
      if(action==='send_reference'&&!/^[a-f0-9]{32}$/.test(v.selection_id||''))throw new Error('Preview a reference before sending');
      if(action==='chapter_browse'&&(!Number.isInteger(v.page)||v.page<0||v.page>24))throw new Error('Invalid chapter page');
      operatorPayload=v;
    }
    if(['preview_suggestion','dismiss_suggestion','clear_suggestions','clear_history'].includes(action)){
      const key=action==='clear_history'?'history_revision':action==='clear_suggestions'?'revision':'suggestion_id';
      const v=operatorChange;
      if(!v||typeof v!=='object'||Array.isArray(v)||Object.keys(v).length!==1||!/^[a-f0-9]{32}$/.test(v[key]||''))throw new Error('Invalid review action');
      operatorPayload={[key]:v[key]};
    }
    if(action==='connection_action'){
      const v=operatorChange,ops=['cancel','prepare_atem','prepare_export','import','local_test','local_warm','atem_discover','atem_on','atem_off'];
      if(!v||typeof v!=='object'||Array.isArray(v)||!ops.includes(v.operation))throw new Error('Invalid connection action');
      const keys=v.operation==='cancel'?['operation']:['operation','settings_revision',...(['local_test','local_warm'].includes(v.operation)?['role']:['atem_on','atem_off'].includes(v.operation)?['review_id','isolated']:v.operation==='prepare_export'?['include_credentials']:v.operation==='import'?['attachment_id','include_credentials']:[])];
      if(Object.keys(v).some(k=>!keys.includes(k))||keys.some(k=>!Object.hasOwn(v,k)))throw new Error('Invalid connection fields');
      for(const k of ['settings_revision','review_id','attachment_id'])if(k in v&&!/^[a-f0-9]{32}$/.test(v[k]||''))throw new Error('Reload the current connection state');
      if('isolated'in v&&v.isolated!==true)throw new Error('Approve the exact isolated target first');
      if('include_credentials'in v&&typeof v.include_credentials!=='boolean')throw new Error('Choose credential scope');
      if('role'in v&&!['verse','outline','summary','watcher'].includes(v.role))throw new Error('Invalid model role');
      operatorPayload=v;
    }
    if(['generate_notes','cancel_notes','prepare_export','prepare_memory_clear','clear_memory'].includes(action)){
      const v=operatorChange||{};
      const keys=action==='prepare_export'?['revision','kind']:['generate_notes','clear_memory'].includes(action)?['revision']:[];
      if(!v||typeof v!=='object'||Array.isArray(v)||Object.keys(v).some(k=>!keys.includes(k))||keys.some(k=>!Object.hasOwn(v,k)))throw new Error('Invalid notes request');
      if(keys.includes('revision')&&!/^[a-f0-9]{32}$/.test(v.revision||''))throw new Error('Review the latest notes first');
      if(action==='prepare_export'&&!['notes','transcript','references','all'].includes(v.kind))throw new Error('Invalid export choice');
      operatorPayload=v;
    }
    const snapshot = await this.reader.poll();
    const session = snapshot.session;
    const control = session?.control;
    if (snapshot.connection !== 'connected' || session?.session_id !== sessionId || !control
      || this.clock() - Date.parse(session.updated_at) > 6000 || control.state === 'closed') {
      throw new Error('Detector session unavailable; refresh before acting');
    }
    if (['set_ask_before_sending', 'start', 'stop', 'save_settings', 'panic', 'restore_session', 'discard_session', 'send_suggestion', 'edit_outline', 'start_bot', 'stop_bot', 'pull_settings', 'list_sessions', 'preview_session', 'resume_saved', 'save_session', 'set_worship', 'emergency_save', 'set_context', 'verse_preview', 'chapter_browse', 'send_reference', 'preview_suggestion', 'dismiss_suggestion', 'clear_suggestions', 'clear_history', 'grid_preview', 'connection_action', 'generate_notes', 'cancel_notes', 'prepare_export', 'prepare_memory_clear', 'clear_memory', 'new_session'].includes(action) ? !control.actions.includes(action)
      : control.state !== 'running' || !control.pending.some(item => item.candidate_id === candidateId)) {
      throw new Error('Action is no longer available');
    }
    if (action === 'save_settings' && (control.state !== 'stopped' || control.settings?.revision !== settingsChange.revision)) {
      throw new Error('Settings changed or engine is running; reload before saving');
    }
    if (recoveryAction && (control.state !== 'stopped' || control.recovery?.revision !== recoveryRevision)) {
      throw new Error('Recovery changed or engine is running; refresh before acting');
    }
    if (action === 'send_suggestion' && (control.state !== 'running' || !control.suggestions?.active || control.suggestions.busy
      || !control.suggestions.rows.some(row => row.id === suggestionId && row.state === 'available'))) {
      throw new Error('Suggestion is no longer available');
    }
    if(action==='edit_outline'&&(!['running','stopped'].includes(control.state)||control.outline?.revision!==outlineChange.revision)){
      throw new Error('Outline changed or editing is unavailable; reload the latest notes');
    }
    const directory = path.join(this.reader.directory, `control-${session.pid}-${control.id}`);
    const stat = await fs.promises.lstat(directory);
    if (!stat.isDirectory() || stat.isSymbolicLink()) throw new Error('Invalid detector inbox');
    const id = randomUUID().replaceAll('-', '');
    const request = { id, control_id: control.id, session_id: sessionId, action, created_at: this.clock() / 1000,
      ...(['approve', 'reject'].includes(action) ? { candidate_id: candidateId } : {}),
      ...(action === 'save_settings' ? { settings_revision: settingsChange.revision, changes } : {}),
      ...(recoveryAction ? { recovery_revision: recoveryRevision } : {}),
      ...(action === 'send_suggestion' ? { suggestion_id:suggestionId } : {}),
      ...(action==='edit_outline'?{outline_revision:outlineChange.revision,outline_text:outlineChange.text}:{}), ...operatorPayload };
    const temporary = path.join(directory, `.command-${id}.tmp`);
    try {
      await fs.promises.writeFile(temporary, JSON.stringify(request), { encoding: 'utf8', mode: 0o600, flag: 'wx' });
      await fs.promises.rename(temporary, path.join(directory, `command-${id}.json`));
    } finally { await fs.promises.unlink(temporary).catch(error => { if (error.code !== 'ENOENT') throw error; }); }
    if (['start', 'clear_memory', 'new_session'].includes(action)) this.reader.commandTransition = { id, pid: session.pid, controlId: control.id,
      sessionId, deadline: this.clock() + 12000 };
    // This acknowledges only the local write. Result and engine status arrive through the feed.
    return { id, action, outcome: 'submitted' };
  }
}
module.exports = { EngineCommands };
