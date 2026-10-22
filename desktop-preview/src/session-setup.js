(() => {
 'use strict';
 const root=document.getElementById('verseview-prototype'),policy=window.sessionPolicy;
 const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const days=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
 let startup={enabled:false,permission:'unknown'},phase='',seconds=8,timer=null,stopped=false;
 const refresh=()=>root.dispatchEvent(new Event('preview:observer'));
 const opts=(items,value)=>items.map(([key,label])=>`<option value="${esc(key)}" ${key===value?'selected':''}>${esc(label)}</option>`).join('');
 function settings(v,locked,s){
  const off=locked?'disabled':'',ml=(v.language==='Malayalam'&&v.stt_engine==='sarvam')||(v.dual_stt_enabled&&v.secondary_language==='ml'&&v.secondary_stt_engine==='sarvam');
  const summary=s.session?.control?.session_setup;
  return `<fieldset class="vv-detection-settings vv-session-fields"><legend>Language and transcript display</legend><label>Show speech as<select data-detector-setting="desktop_transcript_display" ${off}>${opts([['original','Provider transcription'],['translation','English translation when available'],['transliteration','Transliteration when available']],v.desktop_transcript_display)}</select></label><label class="vv-detection-option"><span><input type="checkbox" data-detector-setting="malayalam_transliteration" ${v.malayalam_transliteration?'checked':''} ${off}> Request Malayalam transliteration from Sarvam</span><span class="vv-caption">${ml?'Available for the selected Malayalam/Sarvam stream.':'Requires a Malayalam/Sarvam stream.'} Applies on next Start. Sarvam returns Manglish in this mode. Display choices use supplied text only; unavailable translations or script are labeled.</span></label></fieldset>
  <fieldset class="vv-detection-settings vv-session-fields"><legend>Session and startup</legend><label class="vv-detection-option"><span><input type="checkbox" data-startup-enabled ${startup.enabled?'checked':''}> Start listening automatically on the next app launch</span><span class="vv-caption">This computer only. Starts after an eight-second countdown next time you open the app. You can cancel. Saved recovery or setup issues pause listening; Stop never restarts it.</span></label><p class="vv-caption" data-startup-status>Microphone permission: ${esc(startup.permission)}. ${esc(phase)}</p></fieldset>
  <fieldset class="vv-detection-settings vv-session-fields"><legend>Smart Schedule</legend><label class="vv-detection-option"><span><input type="checkbox" data-detector-setting="smart_schedule" ${v.smart_schedule?'checked':''} ${off}> Select speech languages from the timetable on Start</span></label><label>Time zone<input data-detector-setting="schedule_timezone" maxlength="80" value="${esc(v.schedule_timezone)}" ${off}><span class="vv-caption">Use system for this computer’s clock, UTC, or a supported zone such as America/Chicago.</span></label><div class="vv-schedule-rows">${v.service_schedule.map((r,i)=>`<div class="vv-schedule-row"><label>Day<select data-schedule-index="${i}" data-schedule-field="day" ${off}>${opts(days.map((d,k)=>[k,d]),r.day)}</select></label><label>From<input type="time" value="${r.time}" data-schedule-index="${i}" data-schedule-field="time" ${off}></label><label>Language<select data-schedule-index="${i}" data-schedule-field="language" ${off}>${opts(['English','Malayalam','Hindi'].map(x=>[x,x]),r.language)}</select></label><button type="button" class="vv-btn" data-schedule-remove="${i}" ${off}>Remove</button></div>`).join('')}</div><div class="vv-control-actions"><button type="button" class="vv-btn" data-schedule-add ${locked||v.service_schedule.length>=16?'disabled':''}>Add time</button><button type="button" class="vv-btn" data-schedule-reset ${off}>Restore original timetable</button></div><p class="vv-caption">Up to 16 entries. Each choice lasts until midnight or the next entry. Other times use your saved speech setup. English uses one stream; Malayalam/Hindi add English. Choose a primary provider that supports the scheduled language. This timetable never starts listening or switches an active session.</p>${summary?`<p class="vv-caption" data-schedule-preview>Saved next-Start preview · ${esc(summary.clock)} · ${esc(summary.timezone)}: ${esc(summary.language)} / ${esc(summary.provider)}${summary.dual?` + ${esc(summary.secondary_language)} / ${esc(summary.secondary_provider)}`:' · one stream'}. ${esc(summary.problem||summary.message)}</p>`:''}</fieldset>
  <fieldset class="vv-detection-settings vv-session-fields"><legend>Panic shortcut · clear presentation</legend><label>Shortcut<input data-detector-setting="desktop_panic_shortcut" maxlength="60" value="${esc(v.desktop_panic_shortcut)}" ${off}></label><button type="button" class="vv-btn" data-shortcut-reset ${off}>Reset to Shift+Escape</button><p class="vv-caption">Works while this window is active. Use Shift+Escape, a modified F1–F12 key, or Control/Alt/Meta plus Shift and a letter. Example: Control+Shift+P. Meta means Command on Mac or the Windows key. Reserved shortcuts are rejected; dialogs and typing keep their normal keys. Clears the presentation while listening continues.</p></fieldset>`;
 }
 function banner(snapshot){const v=snapshot?.session?.control?.settings?.values,p=snapshot?.session?.control?.session_setup;const next=v?.smart_schedule&&p?`<p class="vv-caption" data-live-schedule-preview>Next Start · ${esc(p.clock)} (${esc(p.timezone)}): ${esc(p.language)} / ${esc(p.provider)}${p.dual?' + '+esc(p.secondary_language)+' / '+esc(p.secondary_provider):' · one stream'}. ${p.problem?esc(p.problem):p.status==='invalid'?esc(p.message):'Current listening streams will not change.'}</p>`:'';return next+(phase?`<p class="vv-caption vv-startup-notice" role="status">${esc(phase)}${timer?` <button type="button" class="vv-btn" data-startup-cancel>Cancel automatic start</button>`:''}</p>`:'');}
 function cancel(cancelPreparation=true){stopped=true;if(timer)clearInterval(timer);timer=null;if(cancelPreparation)window.consumerFlow?.cancel();phase='Automatic start cancelled for this launch. Listening will not restart automatically.';window.verseviewDesktop?.startup?.('cancel').catch(()=>{});refresh();}
 async function init(){
  if(!window.verseviewDesktop?.startup)return;
  try{
   startup=await window.verseviewDesktop.startup('claim');
   if(!startup.claimed){refresh();return;}
   if(startup.permission!=='granted'){phase='Automatic start paused: microphone permission is not granted. Use Start listening when ready.';refresh();return;}
   phase='Automatic start preparing settings. Listening is stopped.';refresh();await window.consumerFlow.prepare(false);
   if(stopped)return;
   const s=window.previewShell.getObserver(),c=s.session?.control;
   if(s.connection!=='connected'||!c||c.session_setup?.problem||c.session_setup?.status==='invalid'||['available','invalid','staged'].includes(c.recovery?.status)||['failed','conflict'].includes(c.sync?.status)){
    phase=c?.session_setup?.problem?'Automatic start paused: '+c.session_setup.problem:'Automatic start paused. Resolve recovery, connection or settings sync, then press Start listening.';refresh();return;
   }
   phase=`Automatic listening starts in ${seconds} seconds. Review speech setup or cancel.`;refresh();
   timer=setInterval(async()=>{
    if(stopped){clearInterval(timer);timer=null;return;}
    seconds--;phase=`Automatic listening starts in ${seconds} seconds. Review speech setup or cancel.`;refresh();
    if(seconds<=0){clearInterval(timer);timer=null;phase='Automatic Start requested once; readiness checks still apply.';refresh();await window.consumerFlow.prepare(true);}
   },1000);
  }catch{phase='Automatic start unavailable. Listening stays stopped; use Start listening when ready.';refresh();}
 }
 root.addEventListener('input',e=>{if(timer&&e.target.matches('[data-detector-setting],[data-schedule-field]'))cancel();});
 root.addEventListener('change',async e=>{if(!e.target.matches('[data-startup-enabled]'))return;const enabled=e.target.checked;try{startup=await window.verseviewDesktop.startup('set',enabled);if(!enabled&&timer)cancel();else phase=enabled?'Auto-start saved for the next app launch.':'Auto-start is off.';}catch{phase='Startup preference could not be saved. Review it before closing.';}refresh();});
 root.addEventListener('click',e=>{if(e.target.closest('[data-startup-cancel]'))cancel();if(timer&&e.target.closest('[data-consumer-prepare="start"],[data-live-stop],[data-operator="emergency"]'))cancel(false);},{capture:true});
 document.addEventListener('keydown',e=>{
  if(window.previewShell?.getMode()!=='observer'||document.querySelector('dialog[open]')||e.defaultPrevented)return;
  const s=window.previewShell.getObserver(),binding=s.session?.control?.settings?.values?.desktop_panic_shortcut||'Shift+Escape';
  if(!policy.matches(e,binding)||e.key!=='Escape'&&e.target.closest?.('input,textarea,select,[contenteditable="true"]'))return;
  if(s.connection==='connected'&&s.session?.control?.actions.includes('panic')){e.preventDefault();window.verseviewDesktop.clearOutput(s.session.session_id).catch(()=>{});}
 });
 window.sessionSetup=Object.freeze({settings,banner,cancel});
 setTimeout(init,0);
})();
