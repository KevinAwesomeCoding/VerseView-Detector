(() => {
  'use strict';
  const policy=window.cloudPolicy,root=document.getElementById('verseview-prototype');
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const copy=v=>JSON.parse(JSON.stringify(v));
  const labels={verse:'Verse detection and semantic checks',watcher:'English context watcher',watcher_malayalam:'Malayalam context watcher',outline:'Live outline',summary:'Sermon summaries'};
  const credentialLabels={groq_api_key:'Groq API key',gemini_api_key:'Gemini API key',cloudflare_api_token:'Cloudflare API token',cloudflare_account_id:'Cloudflare account ID'};
  let draft=null;
  const dirty=()=>draft&&JSON.stringify(draft.values)!==JSON.stringify(draft.base);
  const refresh=()=>root.dispatchEvent(new Event('preview:observer'));
  function sync(snapshot){
    const c=snapshot.session?.control,s=c?.settings;
    if(!s?.cloud){draft=null;return;}
    if(!draft||draft.host!==c.id)draft={host:c.id,revision:s.revision,base:copy(s.cloud),values:copy(s.cloud),notice:'',pending:null,conflict:false};
    const result=c.results.find(r=>r.id===draft.pending?.id);
    if(result){draft.pending=null;draft.notice=result.reason;if(result.outcome==='saved'){draft.base=copy(s.cloud);draft.values=copy(s.cloud);draft.revision=s.revision;draft.conflict=false;}}
    if(s.revision!==draft.revision){if(dirty()||hasCredentials())draft.conflict=true;else{draft.base=copy(s.cloud);draft.values=copy(s.cloud);draft.revision=s.revision;}}
  }
  function hasCredentials(){return [...root.querySelectorAll('[data-cloud-credential]')].some(e=>!!e.value);}
  function error(){
    if(!draft)return '';
    try{
      const {credentials,...v}=draft.values;policy.validate(v);
      if(v.enabled&&Object.values(v.routes).some(r=>!v.confirmed.includes(r.split('|')[0])))return 'Confirm the free account for each selected provider before enabling free-only routing.';
      return '';
    }catch{return 'Check the Drive download URL and numeric limits. Limits can only be lowered.';}
  }
  function editable(s){return s.connection==='connected'&&s.session?.host?.managed&&s.session.control.state==='stopped'&&s.session.control.actions.includes('save_settings');}
  function render(snapshot){
    sync(snapshot);
    if(!draft||!snapshot.session?.host?.managed)return '';
    const v=draft.values,locked=!editable(snapshot)||!!draft.pending;
    const select=(role,options)=>`<label>${labels[role]}<select data-cloud-route="${role}" ${locked?'disabled':''}>${options.map(pair=>`<option value="${esc(pair)}" ${v.routes[role]===pair?'selected':''}>${esc(pair.replace('|',' · '))}</option>`).join('')}</select></label>`;
    return `<section class="vv-panel vv-detector-settings" aria-label="Cloud providers"><div class="vv-panel-head"><h2>Cloud providers</h2><span class="vv-badge">${v.enabled?'Free-only routing':'Legacy routing'}</span></div>
      <p class="vv-caption">Changes apply on the next engine start. Free-only routing never switches to a paid model. Speech transcription still uses your selected speech provider and its separate allowance.</p>
      <form data-cloud-form novalidate>
        <label class="vv-settings-dual"><input type="checkbox" data-cloud-enabled ${v.enabled?'checked':''} ${locked?'disabled':''}> Use free-only cloud routing</label>
        <p class="vv-caption">Turning this off restores the existing provider configuration, which may use credits. No account or billing plan is changed here.</p>
        <div class="vv-settings-grid">${Object.entries(policy.routes).map(([r,a])=>select(r,a)).join('')}</div>
        <details><summary>Account confirmations and credentials</summary>
          <p class="vv-caption">Confirm each account is on its free plan. Saved keys are never shown. Leave replacement fields empty to keep existing credentials. Saving does not test a provider or start listening.</p>
          ${Object.keys(policy.ceilings).map(p=>`<label class="vv-settings-dual"><input type="checkbox" data-cloud-confirm="${p}" ${v.confirmed.includes(p)?'checked':''} ${locked?'disabled':''}> I have verified my ${esc(p)} account's free plan</label>`).join('')}
          <div class="vv-settings-grid">${policy.credentials.map(k=>`<label>${credentialLabels[k]} · ${v.credentials[k]?'Configured':'Missing'}<input type="password" autocomplete="new-password" spellcheck="false" maxlength="512" data-cloud-credential="${k}" placeholder="Enter replacement to update" ${locked?'disabled':''}></label>`).join('')}</div>
        </details>
        <details><summary>Free usage limits</summary>
          <p class="vv-caption">These are local safety ceilings, not extra provider quota. Requests and tokens are shared across features and streams. Groq reserves 200 daily requests and 40,000 tokens for verse checks; Cloudflare has a 9,000-neuron daily ceiling. Watcher maximum: 1,200 calls/day; summaries: 20 attempts/day. Actual account limits can be lower.</p>
          <div class="vv-settings-grid"><label>Minimum watcher interval across both streams (seconds)<input type="number" min="10" max="300" data-cloud-gap value="${v.watcher_min_gap}" ${locked?'disabled':''}></label>
          ${Object.entries(policy.ceilings).map(([p,caps])=>Object.entries(caps).map(([k,cap])=>`<label>${esc(p)} · ${k==='rpd'?'requests':'tokens'} per rolling 24 hours<input type="number" min="1" max="${cap}" data-cloud-limit="${p}.${k}" value="${v.limits[p][k]}" ${locked?'disabled':''}></label>`).join('')).join('')}</div>
        </details>
        <details open><summary>Drive credential sync</summary><p class="vv-caption">Use the download link for your existing Drive JSON. Sync pulls supported credentials at backend launch or when you click Sync now below. Provider routes stay local. Clear the link to disable startup sync.</p>
          <label>Drive download URL<input type="url" autocomplete="off" spellcheck="false" maxlength="2048" data-cloud-sync value="${esc(v.sync_url)}" placeholder="https://drive.google.com/uc?export=download&amp;id=…" ${locked?'disabled':''}></label>
        </details>
        <p class="vv-caption" role="status" data-cloud-status>${esc(draft.conflict?'Settings changed elsewhere. Reload before saving.':draft.pending?'Saving cloud settings…':draft.notice||error()||'Credentials stay private. Recognition remains stopped.')}</p>
        <div class="vv-control-actions"><button class="vv-btn vv-btn-primary" type="submit" data-cloud-save ${locked||draft.conflict||error()||(!dirty()&&!hasCredentials())?'disabled':''}>Save cloud settings</button><button class="vv-btn" type="button" data-cloud-reload ${draft.pending?'disabled':''}>Reload</button></div>
      </form></section>`;
  }
  function updateAvailability(s){
    sync(s);if(!draft)return;
    const locked=!editable(s)||!!draft.pending;
    for(const e of root.querySelectorAll('[data-cloud-form] input,[data-cloud-form] select'))e.disabled=locked;
    const b=root.querySelector('[data-cloud-save]');if(b)b.disabled=locked||draft.conflict||!!error()||(!dirty()&&!hasCredentials());
  }
  root.addEventListener('input',e=>{
    if(!draft||!e.target.closest('[data-cloud-form]'))return;
    const t=e.target,v=draft.values;
    if(t.hasAttribute('data-cloud-enabled'))v.enabled=t.checked;
    if(t.dataset.cloudRoute)v.routes[t.dataset.cloudRoute]=t.value;
    if(t.dataset.cloudConfirm)v.confirmed=t.checked?[...new Set([...v.confirmed,t.dataset.cloudConfirm])]:v.confirmed.filter(p=>p!==t.dataset.cloudConfirm);
    if(t.hasAttribute('data-cloud-gap'))v.watcher_min_gap=Number(t.value);
    if(t.dataset.cloudLimit){const[p,k]=t.dataset.cloudLimit.split('.');v.limits[p][k]=Number(t.value);}
    if(t.hasAttribute('data-cloud-sync'))v.sync_url=t.value;
    draft.notice='';refresh();
  });
  root.addEventListener('click',e=>{if(e.target.closest('[data-cloud-reload]')&&!draft?.pending){for(const f of root.querySelectorAll('[data-cloud-credential]'))f.value='';draft=null;refresh();}});
  root.addEventListener('submit',async e=>{
    if(!e.target.matches('[data-cloud-form]'))return;e.preventDefault();
    const s=window.previewShell.getObserver();sync(s);
    if(!draft||draft.pending||draft.conflict||!editable(s)||error())return;
    const {credentials:presence,...values}=copy(draft.values);
    values.credentials=Object.fromEntries([...root.querySelectorAll('[data-cloud-credential]')].filter(f=>f.value).map(f=>[f.dataset.cloudCredential,f.value]));
    try{policy.validate(values);}catch{draft.notice='Check replacement credentials. Spaces and control characters are not allowed.';refresh();return;}
    const owner=draft;owner.pending={id:null};
    for(const f of root.querySelectorAll('[data-cloud-credential]'))f.value='';
    refresh();
    try{const result=await window.verseviewDesktop.saveSettings(s.session.session_id,owner.revision,{cloud_settings:values});if(draft===owner)owner.pending=result;}
    catch{if(draft===owner){owner.pending=null;owner.notice='Cloud settings were not submitted. Check the connection and reload before trying again.';}}
    finally{values.credentials={};refresh();}
  });
  window.cloudSettings=Object.freeze({render,updateAvailability});
})();
