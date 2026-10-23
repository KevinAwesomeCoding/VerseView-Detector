(() => {
  'use strict';
  const preferenceKey = 'verseview-desktop-preview.preferences.v1';
  const themeNames = ['sage', 'midnight', 'glass', 'galaxy', 'aurora', 'ember'];
  let preferences = { theme: 'glass', themeChosen: false, layout: 'studio', mode: 'observer', developer: false };
  try {
    const stored = JSON.parse(localStorage.getItem(preferenceKey));
    if (themeNames.includes(stored?.theme)) {
      preferences.theme = stored.theme;
      // Older versions persisted selected themes without a separate choice flag.
      preferences.themeChosen = stored.themeChosen !== false;
    }
    if (['studio', 'focus'].includes(stored?.layout)) preferences.layout = stored.layout;
    if (['samples', 'observer'].includes(stored?.mode)) preferences.mode = stored.mode;
    preferences.developer = stored?.developer === true;
  } catch { /* Corrupt or unavailable storage must not prevent launch. */ }
  const root = document.getElementById('verseview-prototype');
  const surface = document.getElementById('preview-surface');
  const layout = document.getElementById('preview-layout');
  const mode = document.getElementById('preview-mode');
  const updateTools = document.getElementById('preview-update-tools');
  const updateButton = document.getElementById('preview-update');
  const updateStatus = document.getElementById('preview-update-status');
  const updatePrompt = document.getElementById('preview-update-prompt');
  const updatePromptMessage = document.getElementById('preview-update-prompt-message');
  const updatePromptNotes = document.getElementById('preview-update-prompt-notes');
  const updatePromptLater = document.getElementById('preview-update-prompt-later');
  const updatePromptApply = document.getElementById('preview-update-prompt-apply');
  const updatePromptChangelog = document.getElementById('preview-update-prompt-changelog');
  const promptedReleaseKey = 'verseview-desktop-preview.prompted-release.v1';
  let promptedReleaseTag;
  try { promptedReleaseTag = localStorage.getItem(promptedReleaseKey); } catch { /* Session-only reminder. */ }
  let currentUpdate;
  let updateSerial = 0;
  function openUpdatePrompt() {
    if (!currentUpdate?.tag || !updatePrompt) return;
    promptedReleaseTag = currentUpdate.tag;
    try { localStorage.setItem(promptedReleaseKey, promptedReleaseTag); } catch { /* Session-only reminder. */ }
    if (!updatePrompt.open) updatePrompt.showModal();
  }
  function showUpdate(value) {
    if (!updateTools || !updateButton || !updateStatus) return;
    updateSerial++;
    const phase = value?.phase;
    currentUpdate = phase === 'available' ? value : undefined;
    updateTools.hidden = !['available', 'downloading', 'verified', 'installing', 'error'].includes(phase);
    updateButton.disabled = phase !== 'available';
    updateButton.textContent = phase === 'available' ? 'Update' : phase === 'downloading' ? `Downloading ${value.percent || 0}%…`
      : phase === 'verified' ? 'Verifying…' : phase === 'installing' ? 'Installing…' : 'Check again';
    updateStatus.textContent = phase === 'available' ? `${value.prerelease ? 'Beta ' : ''}${value.tag || ''} available`
      : phase === 'error' ? value.message || 'Update failed' : '';
    updateStatus.title = updateStatus.textContent;
    if (phase === 'error') updateButton.disabled = false;
    if (phase === 'available' && value.tag) {
      if (updatePromptMessage) updatePromptMessage.textContent = `${value.prerelease ? 'Beta' : 'Release'} ${value.tag} is ready. Would you like to update now?`;
      if (updatePromptNotes) updatePromptNotes.textContent = value.notes || 'A written summary is unavailable for this release. Open the full changelog to see every change since your installed version.';
      if (value.tag !== promptedReleaseTag) openUpdatePrompt();
    } else if (updatePrompt?.open) {
      updatePrompt.close();
    }
  }
  async function startUpdate() {
    if (!window.verseviewDesktop) return;
    updateButton.disabled = true;
    if (updatePrompt?.open) updatePrompt.close();
    if (updateButton.textContent === 'Check again') await window.verseviewDesktop.checkUpdate();
    else await window.verseviewDesktop.applyUpdate();
  }
  updateButton?.addEventListener('click', () => {
    if (updateButton.textContent === 'Check again') startUpdate();
    else openUpdatePrompt();
  });
  updatePromptApply?.addEventListener('click', startUpdate);
  updatePromptLater?.addEventListener('click', () => updatePrompt.close());
  updatePromptChangelog?.addEventListener('click', () => window.verseviewDesktop?.openUpdateChangelog());
  let observer = { connection: 'waiting', message: 'Waiting for an observer-enabled detector', sources: [], session: null };
  let environment = { platform: 'browser', version: '0.1.0', packaged: false, appearance: { mode: 'solid', reason: 'Browser preview' } };
  let backend = { status: 'unavailable', message: 'Checking bundled backend availability', owned: false };
  let appliedTheme;
  let requestSerial = 0;

  function persist() {
    try { localStorage.setItem(preferenceKey, JSON.stringify(preferences)); } catch { /* Session-only preferences. */ }
  }
  function applyAppearance(value) {
    environment.appearance = value;
    root.dataset.backdrop = value.mode;
    root.dataset.reducedTransparency = String(Boolean(value.reducedTransparency || value.highContrast));
    root.dispatchEvent(new CustomEvent('preview:environment', { detail: environment }));
  }
  function setLayout(value) {
    preferences.layout = value === 'focus' ? 'focus' : 'studio';
    surface.dataset.layout = preferences.layout;
    surface.classList.toggle('vv-focus', preferences.layout === 'focus');
    layout.value = preferences.layout;
    persist();
  }
  layout.addEventListener('change', () => {
    setLayout(layout.value);
    root.dispatchEvent(new Event('preview:layout'));
  });
  document.getElementById('preview-reset').addEventListener('click', () => root.dispatchEvent(new Event('preview:reset')));
  function setMode(value) {
    preferences.mode = value === 'samples' && preferences.developer ? 'samples' : 'observer';
    mode.value = preferences.mode;
    document.getElementById('preview-reset').hidden = preferences.mode !== 'samples';
    persist();
    root.dispatchEvent(new Event('preview:mode'));
  }
  mode.addEventListener('change', () => setMode(mode.value));
  setMode(preferences.mode);
  setLayout(preferences.layout);

  root.dataset.developer=String(preferences.developer);
  window.previewShell = Object.freeze({
    initialTheme: preferences.theme,
    getIconTheme: () => preferences.themeChosen ? preferences.theme : 'original',
    getMode: () => preferences.mode,
    setMode,
    setLayout: value => {setLayout(value);root.dispatchEvent(new Event('preview:layout'));},
    getLayout: () => preferences.layout,
    isDeveloper: () => preferences.developer,
    setDeveloper: value => {
      preferences.developer=value===true;
      root.dataset.developer=String(preferences.developer);
      if(!preferences.developer)setMode('observer');
      persist();root.dispatchEvent(new Event('preview:developer'));
    },
    getObserver: () => observer,
    getEnvironment: () => environment,
    getBackend: () => backend,
    setTheme: async (theme, explicit = false) => {
      if (!themeNames.includes(theme)) return;
      if (explicit) preferences.themeChosen = true;
      const selection = `${theme}:${preferences.themeChosen}`;
      if (appliedTheme === selection) return;
      appliedTheme = selection;
      preferences.theme = theme;
      persist();
      const serial = ++requestSerial;
      // Keep solid until the native shell has acknowledged the effect.
      root.dataset.backdrop = 'solid';
      try {
        const result = window.verseviewDesktop
          ? await window.verseviewDesktop.setTheme(theme, preferences.themeChosen)
          : { mode: 'solid', theme, reason: 'Native glass requires the desktop app' };
        if (serial === requestSerial) applyAppearance(result);
      } catch {
        if (serial === requestSerial) applyAppearance({ mode: 'solid', theme, reason: 'Native effect unavailable' });
      }
    }
  });
  if (window.verseviewDesktop) {
    window.verseviewDesktop.onUpdateChanged(showUpdate);
    const initialUpdateSerial = updateSerial;
    window.verseviewDesktop.updateState().then(value => {
      if (updateSerial === initialUpdateSerial) showUpdate(value);
    }).catch(() => {});
    const updateBackend = value => { backend = value; root.dispatchEvent(new Event('preview:backend')); };
    window.verseviewDesktop.onBackendChanged(updateBackend);
    window.verseviewDesktop.backendState().then(updateBackend).catch(() => {});
    const updateObserver = value => { observer = value; root.dispatchEvent(new Event('preview:observer')); };
    window.verseviewDesktop.onObserverChanged(updateObserver);
    window.verseviewDesktop.observer().then(updateObserver).catch(() => {
      updateObserver({ connection: 'unavailable', message: 'Observer connection unavailable', sources: [], session: null });
    });
    window.verseviewDesktop.onAppearanceChanged(value => {
      if (value.theme === preferences.theme) applyAppearance(value);
    });
    window.verseviewDesktop.environment().then(value => {
      environment = value;
      root.dataset.platform = value.platform;
      if (value.appearance?.theme === preferences.theme) applyAppearance(value.appearance);
      root.dispatchEvent(new CustomEvent('preview:environment', { detail: environment }));
    }).catch(() => {});
  }
})();
