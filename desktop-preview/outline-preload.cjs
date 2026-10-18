'use strict';
const {contextBridge,ipcRenderer}=require('electron');
contextBridge.exposeInMainWorld('outlineDisplay',Object.freeze({
  onText:callback=>{
    const listener=(_event,value)=>{if(typeof value?.text==='string')callback(value.text.slice(0,4000));};
    ipcRenderer.on('preview:outline-text',listener);
    return ()=>ipcRenderer.removeListener('preview:outline-text',listener);
  }
}));
