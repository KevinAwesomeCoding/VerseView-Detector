/* Shared local session policy. No provider calls or OS shortcut registration. */
(function(root){
 'use strict';
 const schedule=[{day:5,time:'00:00',language:'Malayalam'},{day:6,time:'09:10',language:'English'},{day:6,time:'10:40',language:'Malayalam'},{day:6,time:'16:40',language:'Hindi'}];
 const defaults={malayalam_transliteration:false,show_malayalam_raw:false,desktop_transcript_display:'original',smart_schedule:false,service_schedule:schedule,schedule_timezone:'system',desktop_panic_shortcut:'Shift+Escape'};
 function shortcut(value){
  if(typeof value!=='string'||value.length>60)return false;
  const parts=value.split('+'),key=parts.pop(),order=['Control','Alt','Meta','Shift'];
  if(!parts.length)return /^F([1-9]|1[0-2])$/.test(key);
  if(parts.join('+')!==order.filter(m=>parts.includes(m)).join('+')||!/^(Escape|F([1-9]|1[0-2])|[A-Z])$/.test(key))return false;
  if(key==='Escape')return value==='Shift+Escape';
  if(/^[A-Z]$/.test(key)&&(!parts.includes('Shift')||!parts.some(m=>['Control','Alt','Meta'].includes(m))))return false;
  return !['Alt+F4','Meta+Shift+Q','Control+Shift+I','Control+Shift+J','Control+Shift+C'].includes(value);
 }
 function validRules(rows){
  if(!Array.isArray(rows)||rows.length>16)return false;const seen=new Set();
  return rows.every(r=>{if(!r||Object.keys(r).sort().join(',')!=='day,language,time'||!Number.isInteger(r.day)||r.day<0||r.day>6||!['English','Malayalam','Hindi'].includes(r.language)||typeof r.time!=='string'||!/^([01]\d|2[0-3]):[0-5]\d$/.test(r.time))return false;const k=`${r.day}:${r.time}`;if(seen.has(k))return false;seen.add(k);return true;});
 }
 function valid(key,v){
  if(['malayalam_transliteration','show_malayalam_raw','smart_schedule'].includes(key))return typeof v==='boolean';
  if(key==='desktop_transcript_display')return ['original','translation','transliteration'].includes(v);
  if(key==='desktop_panic_shortcut')return shortcut(v);
  if(key==='service_schedule')return validRules(v);
  if(key==='schedule_timezone'){if(typeof v!=='string'||v.length>80||!v)return false;if(v==='system'||v==='UTC')return true;try{new Intl.DateTimeFormat('en',{timeZone:v});return true;}catch{return false;}}
  return false;
 }
 function matches(event,value){
  if(!shortcut(value)||event.repeat||event.isComposing)return false;
  const parts=value.split('+'),key=parts.pop();
  return key===String(event.key).toUpperCase().replace(/^ESCAPE$/,'Escape')&&event.ctrlKey===parts.includes('Control')&&event.altKey===parts.includes('Alt')&&event.shiftKey===parts.includes('Shift')&&event.metaKey===parts.includes('Meta');
 }
 function transcript(row,choice){
  const translit=row.text_kind==='transliteration';
  if(choice==='translation'&&row.language!=='en')return row.translation?{text:row.translation,label:'English translation',language:'en'}:{text:row.text,label:'Translation unavailable · provider '+(translit?'transliteration':'transcription'),language:row.language};
  if(choice==='transliteration')return {text:row.text,label:translit?'Provider transliteration (Manglish)':'Transliteration unavailable · provider transcription',language:row.language};
  return {text:row.text,label:translit?'Provider transliteration · Malayalam script was not supplied':'Provider transcription',language:row.language};
 }
 const api=Object.freeze({defaults,valid,validRules,shortcut,matches,transcript});
 if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.sessionPolicy=api;
})(typeof window!=='undefined'?window:globalThis);
