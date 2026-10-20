'use strict';
// Historical diagnostic harnesses intentionally exercise the advanced surface.
// Consumer-mode defaults and lifecycle behavior are checked independently.
module.exports=async page=>{
 const enable=()=>{
  const key='verseview-desktop-preview.preferences.v1';let preferences={};
  try{preferences=JSON.parse(localStorage.getItem(key))||{};}catch{}
  localStorage.setItem(key,JSON.stringify({...preferences,developer:true}));
  window.previewShell?.setDeveloper?.(true);
 };
 await page.addInitScript(enable);await page.evaluate(enable);
};
