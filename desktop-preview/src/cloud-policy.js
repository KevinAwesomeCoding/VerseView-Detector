/* Reviewed cloud routes and write-only credential boundary. */
(function(root){
  'use strict';
  const groq='groq|qwen/qwen3.8-27b', gemini=['gemini|gemini-3.5-flash-lite','gemini|gemini-3.8-flash'];
  const routes={verse:[groq],watcher:['cloudflare|@cf/qwen/qwen3-30b-a3b-fp8',groq],watcher_malayalam:[groq],outline:gemini,summary:gemini};
  const credentials=['groq_api_key','gemini_api_key','cloudflare_api_token','cloudflare_account_id'];
  const ceilings={groq:{rpd:1000,tpd:200000},cloudflare:{rpd:2000,tpd:1000000},gemini:{rpd:500,tpd:2000000}};
  const object=v=>v&&typeof v==='object'&&!Array.isArray(v);
  function syncURL(v){
    if(typeof v!=='string'||v.length>2048||/[\s\x00-\x1f\x7f]/.test(v))return false;
    if(!v)return true;
    try{const u=new URL(v),q=u.searchParams;return u.protocol==='https:'&&u.hostname==='drive.google.com'&&!u.username&&!u.password&&!u.port&&!u.hash&&u.pathname==='/uc'
      &&[...q.keys()].length===2&&q.get('export')==='download'&&/^[A-Za-z0-9_-]{10,200}$/.test(q.get('id')||'');}catch{return false;}
  }
  function validate(v){
    const fail=()=>{throw new Error('Invalid cloud settings');};
    if(!object(v)||!Object.keys(v).length||Object.keys(v).some(k=>!['enabled','routes','watcher_min_gap','limits','confirmed','sync_url','credentials'].includes(k)))fail();
    if('enabled'in v&&typeof v.enabled!=='boolean')fail();
    if('sync_url'in v&&!syncURL(v.sync_url))fail();
    if('watcher_min_gap'in v&&(!Number.isFinite(v.watcher_min_gap)||v.watcher_min_gap<10||v.watcher_min_gap>300))fail();
    if('confirmed'in v&&(!Array.isArray(v.confirmed)||v.confirmed.some(p=>!Object.hasOwn(ceilings,p))))fail();
    if('routes'in v&&(!object(v.routes)||Object.keys(v.routes).length!==Object.keys(routes).length||Object.entries(routes).some(([k,a])=>!a.includes(v.routes[k]))))fail();
    if('limits'in v&&(!object(v.limits)||Object.keys(v.limits).length!==3||Object.entries(ceilings).some(([p,caps])=>!object(v.limits[p])||Object.keys(v.limits[p]).length!==2||Object.entries(caps).some(([k,cap])=>!Number.isSafeInteger(v.limits[p][k])||v.limits[p][k]<1||v.limits[p][k]>cap))))fail();
    if('credentials'in v&&(!object(v.credentials)||Object.entries(v.credentials).some(([k,s])=>!credentials.includes(k)||typeof s!=='string'||!s.length||s.length>512||/[\s\x00-\x1f\x7f]/.test(s)||(k==='cloudflare_account_id'&&!/^[a-fA-F0-9]{32}$/.test(s)))))fail();
    return JSON.parse(JSON.stringify(v));
  }
  function decode(v){
    if(!object(v))return null;
    try{
      const safe=validate({enabled:v.enabled,routes:v.routes,watcher_min_gap:v.watcher_min_gap,limits:v.limits,confirmed:v.confirmed,sync_url:v.sync_url});
      safe.credentials=Object.fromEntries(credentials.map(k=>[k,v.credentials?.[k]===true]));return safe;
    }catch{return null;}
  }
  const api={routes,credentials,ceilings,syncURL,validate,decode};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.cloudPolicy=api;
})(globalThis);
