'use strict';
const { contextBridge, ipcRenderer } = require('electron');

// Narrow appearance, observation and opt-in controls. No arbitrary filesystem or IPC.
contextBridge.exposeInMainWorld('verseviewDesktop', Object.freeze({
  updateState:()=>ipcRenderer.invoke('preview:update-state'),
  checkUpdate:()=>ipcRenderer.invoke('preview:check-update'),
  applyUpdate:()=>ipcRenderer.invoke('preview:apply-update'),
  openUpdateChangelog:()=>ipcRenderer.invoke('preview:update-changelog'),
  onUpdateChanged:callback=>{
    const listener=(_event,value)=>callback(value);ipcRenderer.on('preview:update-changed',listener);
    return ()=>ipcRenderer.removeListener('preview:update-changed',listener);
  },
  openReleases:()=>ipcRenderer.invoke('preview:releases'),
  profileTransfer:(sessionId,revision,kind,includeCredentials)=>ipcRenderer.invoke('preview:profile-transfer',sessionId,revision,kind,includeCredentials),
  startup:(action,enabled)=>ipcRenderer.invoke('preview:startup',action,enabled),
  exportSession:(sessionId,exportId)=>ipcRenderer.invoke('preview:export-session',sessionId,exportId),
  operator:(sessionId,action,value)=>ipcRenderer.invoke('preview:operator',sessionId,action,value),
  setAlwaysOnTop:enabled=>ipcRenderer.invoke('preview:window-pin',enabled),
  windowState:()=>ipcRenderer.invoke('preview:window-state'),
  environment: () => ipcRenderer.invoke('preview:environment'),
  setTheme: (theme, themedIcon = true) => ipcRenderer.invoke('preview:set-theme', theme, themedIcon),
  startEngine: sessionId => ipcRenderer.invoke('preview:start-engine', sessionId),
  stopEngine: sessionId => ipcRenderer.invoke('preview:stop-engine', sessionId),
  resolveCandidate: (sessionId, candidateId, approved) => ipcRenderer.invoke('preview:resolve-candidate', sessionId, candidateId, approved),
  saveSettings: (sessionId, revision, changes) => ipcRenderer.invoke('preview:save-settings', sessionId, revision, changes),
  clearOutput: sessionId => ipcRenderer.invoke('preview:clear-output', sessionId),
  recoverSession: (sessionId, revision, restore) => ipcRenderer.invoke('preview:recover-session', sessionId, revision, restore),
  sendSuggestion: (sessionId, suggestionId) => ipcRenderer.invoke('preview:send-suggestion', sessionId, suggestionId),
  editOutline:(sessionId,revision,text)=>ipcRenderer.invoke('preview:edit-outline',sessionId,revision,text),
  botControl:(sessionId,action)=>ipcRenderer.invoke('preview:bot-control',sessionId,action),
  pullSettings:sessionId=>ipcRenderer.invoke('preview:pull-settings',sessionId),
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
  transcriptPage: (sessionId, offset) => ipcRenderer.invoke('preview:transcript-page', sessionId, offset),
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
