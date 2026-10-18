'use strict';
const { contextBridge, ipcRenderer } = require('electron');

// Narrow appearance, observation and opt-in controls. No arbitrary filesystem or IPC.
contextBridge.exposeInMainWorld('verseviewDesktop', Object.freeze({
  environment: () => ipcRenderer.invoke('preview:environment'),
  setTheme: theme => ipcRenderer.invoke('preview:set-theme', theme),
  startEngine: sessionId => ipcRenderer.invoke('preview:start-engine', sessionId),
  stopEngine: sessionId => ipcRenderer.invoke('preview:stop-engine', sessionId),
  resolveCandidate: (sessionId, candidateId, approved) => ipcRenderer.invoke('preview:resolve-candidate', sessionId, candidateId, approved),
  saveSettings: (sessionId, revision, changes) => ipcRenderer.invoke('preview:save-settings', sessionId, revision, changes),
  clearOutput: sessionId => ipcRenderer.invoke('preview:clear-output', sessionId),
  recoverSession: (sessionId, revision, restore) => ipcRenderer.invoke('preview:recover-session', sessionId, revision, restore),
  sendSuggestion: (sessionId, suggestionId) => ipcRenderer.invoke('preview:send-suggestion', sessionId, suggestionId),
  editOutline:(sessionId,revision,text)=>ipcRenderer.invoke('preview:edit-outline',sessionId,revision,text),
  outlineOutputState:()=>ipcRenderer.invoke('preview:outline-output-state'),
  openOutlineOutput:(sessionId,target)=>ipcRenderer.invoke('preview:open-outline-output',sessionId,target),
  closeOutlineOutput:()=>ipcRenderer.invoke('preview:close-outline-output'),
  onOutlineOutputChanged:callback=>{
    const listener=(_event,value)=>callback(value);ipcRenderer.on('preview:outline-output-changed',listener);
    return ()=>ipcRenderer.removeListener('preview:outline-output-changed',listener);
  },
  backendState: () => ipcRenderer.invoke('preview:backend-state'),
  launchBackend: () => ipcRenderer.invoke('preview:launch-backend'),
  closeBackend: () => ipcRenderer.invoke('preview:close-backend'),
  openBackendFolder: () => ipcRenderer.invoke('preview:backend-folder'),
  onBackendChanged: callback => {
    const listener = (_event, value) => callback(value);
    ipcRenderer.on('preview:backend-changed', listener);
    return () => ipcRenderer.removeListener('preview:backend-changed', listener);
  },
  observer: () => ipcRenderer.invoke('preview:observer'),
  selectObserver: sessionId => ipcRenderer.invoke('preview:select-observer', sessionId),
  onObserverChanged: callback => {
    const listener = (_event, value) => callback(value);
    ipcRenderer.on('preview:observer-changed', listener);
    return () => ipcRenderer.removeListener('preview:observer-changed', listener);
  },
  onAppearanceChanged: callback => {
    const listener = (_event, value) => callback(value);
    ipcRenderer.on('preview:appearance-changed', listener);
    return () => ipcRenderer.removeListener('preview:appearance-changed', listener);
  }
}));
