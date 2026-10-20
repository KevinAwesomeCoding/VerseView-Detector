'use strict';

const { app, BrowserWindow, ipcMain, Menu, nativeTheme, session, shell, screen } = require('electron');
const path = require('node:path');
const os = require('node:os');
const { pathToFileURL } = require('node:url');
const { DARK_THEMES, validTheme, backdropPolicy, backgroundColor } = require('./appearance.cjs');
const { EngineFeedReader, feedDirectory } = require('./engine-feed.cjs');
const { EngineCommands } = require('./engine-commands.cjs');
const { BackendManager } = require('./backend-manager.cjs');
const { OutlineOutput } = require('./outline-output.cjs');
const fs = require('node:fs');

app.setName('VerseView Desktop Preview');
// Separate from both the production detector and the Electron development app.
app.setPath('userData', path.join(app.getPath('appData'), 'VerseView Desktop Preview'));
if (process.env.VV_PREVIEW_TEST_PROFILE === '1') {
  app.setPath('userData', path.join(app.getPath('userData'), 'QA'));
}
let window;
let outlineOutput;
let theme = 'glass';
let appearance;
let build = { sourceRevision: 'development', buildId: 'development' };
if (app.isPackaged) {
  try { build = require('./build-info.json'); } catch { /* Show unknown provenance if metadata is missing. */ }
}
const pageURL = pathToFileURL(path.join(__dirname, 'src', 'index.html')).href;
const observerDirectory = process.env.VV_PREVIEW_TEST_PROFILE === '1' && process.env.VV_OBSERVER_TEST_DIRECTORY
  ? process.env.VV_OBSERVER_TEST_DIRECTORY
  : feedDirectory({ platform: process.platform, appData: app.getPath('appData'), home: app.getPath('home') });
const observer = new EngineFeedReader({ directory: observerDirectory, onChange: snapshot => {
  if (window && !window.isDestroyed()) window.webContents.send('preview:observer-changed', snapshot);
  outlineOutput?.update(snapshot);
} });

const commands = new EngineCommands(observer);

let backendRoot = path.join(process.resourcesPath, 'backend');
if (!app.isPackaged) {
  try { backendRoot = fs.readFileSync(path.join(__dirname, 'backend-build', 'latest.txt'), 'utf8').trim(); } catch {}
}
const qa = process.env.VV_PREVIEW_TEST_PROFILE === '1';
const backendProfile = path.join(app.getPath('userData'), 'Backend');
const manager = new BackendManager({ root: backendRoot, profile: backendProfile,
  sourceProfile: qa ? (process.env.VV_BACKEND_SOURCE_PROFILE || path.join(backendProfile, 'EmptySource')) : path.dirname(observerDirectory),
  verification: qa && process.env.VV_BACKEND_VERIFY === '1',
  onChange: state => {
    if(state.status!=='ready')outlineOutput?.close();
    if (window && !window.isDestroyed()) window.webContents.send('preview:backend-changed', state);
  } });
function useObserverDirectory(directory) {
  observer.stop(); observer.directory = directory; observer.selected = null; observer.cache.clear();
  observer.signature = ''; observer.start();
}
let quitting = false;

function updateBackdrop() {
  if (!window || window.isDestroyed()) return;
  const reducedTransparency = Boolean(nativeTheme.prefersReducedTransparency);
  const highContrast = Boolean(nativeTheme.shouldUseHighContrastColors || nativeTheme.inForcedColorsMode);
  let policy = backdropPolicy({ platform: process.platform, release: os.release(), theme, reducedTransparency, highContrast });
  try {
    if (process.platform === 'darwin') window.setVibrancy(policy.mode === 'native' ? policy.material : null);
    if (process.platform === 'win32' && Number(os.release().split('.')[2]) >= 22621) {
      window.setBackgroundMaterial(policy.mode === 'native' ? policy.material : 'none');
    }
    window.setBackgroundColor(policy.mode === 'native' ? '#00000000' : backgroundColor(theme, nativeTheme.shouldUseDarkColors));
  } catch (error) {
    // A failed native effect must leave a usable, readable window.
    console.warn('Native backdrop unavailable:', error.message);
    if (process.platform === 'darwin') window.setVibrancy(null);
    policy = { mode: 'solid', reason: 'Native backdrop could not be enabled' };
    window.setBackgroundColor(backgroundColor(theme, nativeTheme.shouldUseDarkColors));
  }
  appearance = { ...policy, theme, dark: nativeTheme.shouldUseDarkColors, reducedTransparency, highContrast };
  window.webContents.send('preview:appearance-changed', appearance);
  return appearance;
}

function trusted(event) {
  return window && event.sender === window.webContents && event.senderFrame === window.webContents.mainFrame
    && event.senderFrame.url === pageURL;
}

ipcMain.handle('preview:environment', event => {
  if (!trusted(event)) throw new Error('Untrusted preview sender');
  return { platform: process.platform, release: os.release(), version: app.getVersion(), packaged: app.isPackaged,
    sourceRevision: build.sourceRevision, buildId: build.buildId, appearance };
});
ipcMain.handle('preview:set-theme', (event, value) => {
  if (!trusted(event) || !validTheme(value)) throw new Error('Invalid appearance request');
  theme = value;
  nativeTheme.themeSource = DARK_THEMES.has(theme) ? 'dark' : 'system';
  return updateBackdrop();
});
ipcMain.handle('preview:observer', event => {
  if (!trusted(event)) throw new Error('Untrusted preview sender');
  return observer.poll();
});
ipcMain.handle('preview:transcript-page', (event, sessionId, offset) => {
  if (!trusted(event)) throw new Error('Untrusted preview sender');
  return observer.transcriptPage(sessionId, offset);
});
ipcMain.handle('preview:select-observer', (event, sessionId) => {
  if (!trusted(event)) throw new Error('Untrusted preview sender');
  return observer.select(sessionId);
});

for (const [channel, action] of [['preview:start-engine', 'start'], ['preview:stop-engine', 'stop'], ['preview:clear-output', 'panic']]) {
  ipcMain.handle(channel, (event, sessionId) => {
    if (!trusted(event)) throw new Error('Untrusted preview sender');
    return commands.submit(sessionId, action);
  });
}
ipcMain.handle('preview:resolve-candidate', (event, sessionId, candidateId, approved) => {
  if (!trusted(event) || typeof approved !== 'boolean') throw new Error('Invalid approval request');
  return commands.submit(sessionId, approved ? 'approve' : 'reject', candidateId);
});

ipcMain.handle('preview:save-settings', (event, sessionId, revision, changes) => {
  if (!trusted(event)) throw new Error('Untrusted preview sender');
  return commands.submit(sessionId, 'save_settings', undefined, { revision, changes });
});
ipcMain.handle('preview:recover-session', (event, sessionId, revision, restore) => {
  if (!trusted(event) || typeof restore !== 'boolean') throw new Error('Invalid recovery request');
  return commands.submit(sessionId, restore ? 'restore_session' : 'discard_session', undefined, undefined, revision);
});
ipcMain.handle('preview:send-suggestion', (event, sessionId, suggestionId) => {
  if (!trusted(event)) throw new Error('Untrusted preview sender');
  return commands.submit(sessionId, 'send_suggestion', undefined, undefined, undefined, suggestionId);
});
ipcMain.handle('preview:edit-outline',(event,sessionId,revision,text)=>{
  if(!trusted(event))throw new Error('Untrusted preview sender');
  return commands.submit(sessionId,'edit_outline',undefined,undefined,undefined,undefined,{revision,text});
});
ipcMain.handle('preview:bot-control',(event,sessionId,action)=>{
  if(!trusted(event)||!['start_bot','stop_bot'].includes(action))throw new Error('Invalid bot control');
  return commands.submit(sessionId,action);
});
ipcMain.handle('preview:pull-settings',(event,sessionId)=>{
  if(!trusted(event))throw new Error('Untrusted preview sender');return commands.submit(sessionId,'pull_settings');
});
ipcMain.handle('preview:outline-output-state',event=>{
  if(!trusted(event))throw new Error('Untrusted preview sender');return outlineOutput.state();
});
ipcMain.handle('preview:open-outline-output',(event,sessionId,target)=>{
  if(!trusted(event))throw new Error('Untrusted preview sender');return outlineOutput.open(sessionId,target);
});
ipcMain.handle('preview:close-outline-output',event=>{
  if(!trusted(event))throw new Error('Untrusted preview sender');return outlineOutput.close();
});

ipcMain.handle('preview:backend-state', event => {
  if (!trusted(event)) throw new Error('Untrusted preview sender');
  return manager.state;
});
ipcMain.handle('preview:launch-backend', async event => {
  if (!trusted(event)) throw new Error('Untrusted preview sender');
  const result = await manager.launch();
  if (result.status === 'ready') {
    useObserverDirectory(path.join(backendProfile, 'Observer'));
    for (let attempt = 0; attempt < 30; attempt++) {
      const snapshot = await observer.poll();
      const source = snapshot.sources.find(item => item.pid === result.pid);
      if (source) { await observer.select(source.session_id); break; }
      await new Promise(resolve => setTimeout(resolve, 100));
    }
  }
  return result;
});
ipcMain.handle('preview:close-backend', async event => {
  if (!trusted(event)) throw new Error('Untrusted preview sender');
  return manager.close();
});
ipcMain.handle('preview:backend-folder', async event => {
  if (!trusted(event) || !fs.existsSync(backendProfile)) throw new Error('Backend profile is unavailable');
  const error = await shell.openPath(backendProfile);
  if (error) throw new Error('Could not open the backend profile folder');
});

function createWindow() {
  window = new BrowserWindow({
    title: 'VerseView Desktop Preview', width: 1180, height: 880, minWidth: 640, minHeight: 540,
    show: false, backgroundColor: '#dce7ef',
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    ...(process.platform === 'darwin' ? { transparent: true, vibrancy: 'under-window', visualEffectState: 'followWindow' } : {}),
    webPreferences: { preload: path.join(__dirname, 'preload.cjs'), nodeIntegration: false, contextIsolation: true,
      sandbox: true, webSecurity: true, spellcheck: false, devTools: !app.isPackaged }
  });
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  window.webContents.on('will-navigate', event => event.preventDefault());
  window.webContents.on('will-attach-webview', event => event.preventDefault());
  window.webContents.on('did-finish-load', updateBackdrop);
  window.once('ready-to-show', () => { updateBackdrop(); window.show(); });
  window.on('closed', () => { window = null; outlineOutput?.close(); });
  updateBackdrop();
  window.loadFile(path.join(__dirname, 'src', 'index.html'));
}

app.whenReady().then(() => {
  outlineOutput=new OutlineOutput({BrowserWindow,screen,readSnapshot:()=>observer.poll(),
    page:path.join(__dirname,'src/outline-display.html'),preload:path.join(__dirname,'outline-preload.cjs'),
    onChange:state=>{if(window&&!window.isDestroyed())window.webContents.send('preview:outline-output-changed',state);}});
  for(const event of ['display-added','display-removed','display-metrics-changed'])screen.on(event,()=>{
    outlineOutput.update(observer.snapshot);
    if(window&&!window.isDestroyed())window.webContents.send('preview:outline-output-changed',outlineOutput.state());
  });
  observer.start();
  session.defaultSession.setPermissionRequestHandler((_contents, _permission, callback) => callback(false));
  session.defaultSession.setPermissionCheckHandler(() => false);
  session.defaultSession.webRequest.onBeforeRequest({ urls: ['http://*/*', 'https://*/*', 'ws://*/*', 'wss://*/*'] },
    (_details, callback) => callback({ cancel: true }));
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    ...(process.platform === 'darwin' ? [{ role: 'appMenu' }] : [{ label: 'File', submenu: [{ role: 'quit' }] }]),
    { role: 'editMenu' },
    { label: 'View', submenu: [{ role: 'resetZoom' }, { role: 'zoomIn' }, { role: 'zoomOut' },
      { type: 'separator' }, { role: 'togglefullscreen' }] },
    { role: 'windowMenu' }
  ]));
  createWindow();
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});
nativeTheme.on('updated', updateBackdrop);
app.on('window-all-closed', () => app.quit());
app.on('before-quit', event => {
  outlineOutput?.close();
  if (quitting) { observer.stop(); return; }
  if (!manager.child) { observer.stop(); return; }
  event.preventDefault();
  manager.close().then(() => { quitting = true; observer.stop(); app.quit(); }).catch(() => {});
});
