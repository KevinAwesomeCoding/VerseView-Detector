(function(root){
 'use strict';
 const defaults={atem_enabled:false,atem_ip:'',atem_key_duration:5,local_whisper_endpoint:'',local_llm_enabled:false,local_llm_endpoint:'',local_llm_model:'',local_llm_timeout:45,local_llm_on_failure:'fallback',local_llm_role_verse:'cloud',local_llm_role_outline:'cloud',local_llm_role_summary:'cloud',local_llm_model_verse:'',local_llm_model_outline:'',local_llm_model_summary:'',local_llm_keep_alive_verse:'30m',local_llm_keep_alive_outline:'15m',local_llm_keep_alive_summary:'10m',local_llm_warm_at_start:false,live_points_llm_enabled:false,live_points_prompt:'',llm_enabled:true,rate:16000,chunk:4096,cooldown:3,dedup_window:60,silence_timeout:60,aai_turn_cutoff:5,gcp_interim_flush:4,vv_guild_id:''};
 const bounds={atem_key_duration:[.1,120],local_llm_timeout:[5,180],chunk:[128,65536],cooldown:[.1,120],dedup_window:[1,3600],silence_timeout:[1,3600],aai_turn_cutoff:[1,60],gcp_interim_flush:[1,60]};
 const secrets=['local_llm_auth_token','local_llm_extra_headers','mistral_api_key','cerebras_api_key','discord_webhook_url','discord_log_webhook_url','discord_notes_webhook_url','discord_bot_token'];
 function endpoint(v){if(typeof v!=='string'||v.length>512||/[\s\x00-\x1f\x7f]/.test(v))return false;if(!v)return true;try{const u=new URL(v);return ['http:','https:'].includes(u.protocol)&&!!u.hostname&&!u.username&&!u.password&&!u.search&&!u.hash;}catch{return false;}}
 function valid(k,v){
  if(['atem_enabled','local_llm_enabled','local_llm_warm_at_start','live_points_llm_enabled','llm_enabled'].includes(k))return typeof v==='boolean';
  if(k in bounds)return typeof v==='number'&&Number.isFinite(v)&&v>=bounds[k][0]&&v<=bounds[k][1]&&(!['chunk','aai_turn_cutoff','gcp_interim_flush'].includes(k)||Number.isInteger(v));
  if(k==='rate')return [8000,16000,22050,24000,32000,44100,48000].includes(v);
  if(k==='atem_ip')return typeof v==='string'&&(!v||/^\d{1,3}(\.\d{1,3}){3}$/.test(v)&&v.split('.').every(n=>String(Number(n))===n&&Number(n)<=255));
  if(['local_llm_endpoint','local_whisper_endpoint'].includes(k))return endpoint(v);
  if(k==='local_llm_on_failure')return ['fallback','skip'].includes(v);
  if(k.startsWith('local_llm_role_'))return ['cloud','local'].includes(v);
  if(k.startsWith('local_llm_keep_alive_'))return typeof v==='string'&&/^(0|[1-9][0-9]{0,3})(s|m|h)?$/.test(v);
  if(k==='live_points_prompt')return typeof v==='string'&&v.length<=8000&&!v.includes('\0');
  if(k==='vv_guild_id')return typeof v==='string'&&(!v||/^[0-9]{5,24}$/.test(v));
  if(k.startsWith('local_llm_model'))return typeof v==='string'&&v.length<=160&&!/[\s\x00-\x1f\x7f]/.test(v);
  return false;
 }
 function validateSecrets(v){if(!v||typeof v!=='object'||Array.isArray(v)||Object.entries(v).some(([k,s])=>!secrets.includes(k)||typeof s!=='string'||s.length>(k==='local_llm_extra_headers'?8192:2048)||s.includes('\0')))throw new Error('Invalid connection credentials');for(const [k,s]of Object.entries(v)){if(k==='local_llm_extra_headers'){let h;try{h=s?JSON.parse(s):{};}catch{throw new Error('Headers must be a JSON object');}if(!h||Array.isArray(h)||typeof h!=='object'||Object.keys(h).length>16||Object.entries(h).some(([a,b])=>!/^[A-Za-z0-9-]{1,80}$/.test(a)||typeof b!=='string'||/[\r\n\0]/.test(b)))throw new Error('Invalid headers');}else if(k.endsWith('_url')){if(s&&(!endpoint(s)||!s.startsWith('https://')))throw new Error('Use an HTTPS webhook');}else if(/[\s\x00-\x1f\x7f]/.test(s))throw new Error('Credential contains whitespace');}return {...v};}
 const api={defaults,bounds,secrets,valid,endpoint,validateSecrets};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.optionsPolicy=api;
})(globalThis);
