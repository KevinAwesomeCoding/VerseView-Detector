(() => {
  'use strict';
  const preferenceKey = 'verseview-desktop-preview.preferences.v1';
  const themeNames = ['sage', 'midnight', 'glass', 'galaxy', 'aurora', 'ember'];
  let preferences = { theme: 'glass', layout: 'studio', mode: 'observer' };
  try {
    const stored = JSON.parse(localStorage.getItem(preferenceKey));
    if (themeNames.includes(stored?.theme)) preferences.theme = stored.theme;
    if (['studio', 'focus'].includes(stored?.layout)) preferences.layout = stored.layout;
    if (['samples', 'observer'].includes(stored?.mode)) preferences.mode = stored.mode;
  } catch { /* Corrupt or unavailable storage must not prevent launch. */ }
  const root = document.getElementById('verseview-prototype');
  const surface = document.getElementById('preview-surface');
  const layout = document.getElementById('preview-layout');
  const mode = document.getElementById('preview-mode');
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
    preferences.mode = value === 'samples' ? 'samples' : 'observer';
    mode.value = preferences.mode;
    document.getElementById('preview-reset').hidden = preferences.mode !== 'samples';
    persist();
    root.dispatchEvent(new Event('preview:mode'));
  }
  mode.addEventListener('change', () => setMode(mode.value));
  setMode(preferences.mode);
  setLayout(preferences.layout);

  window.previewShell = Object.freeze({
    initialTheme: preferences.theme,
    getMode: () => preferences.mode,
    setMode,
    getObserver: () => observer,
    getEnvironment: () => environment,
    getBackend: () => backend,
    setTheme: async theme => {
      if (!themeNames.includes(theme) || appliedTheme === theme) return;
      appliedTheme = theme;
      preferences.theme = theme;
      persist();
      const serial = ++requestSerial;
      // Keep solid until the native shell has acknowledged the effect.
      root.dataset.backdrop = 'solid';
      try {
        const result = window.verseviewDesktop
          ? await window.verseviewDesktop.setTheme(theme)
          : { mode: 'solid', theme, reason: 'Native glass requires the desktop app' };
        if (serial === requestSerial) applyAppearance(result);
      } catch {
        if (serial === requestSerial) applyAppearance({ mode: 'solid', theme, reason: 'Native effect unavailable' });
      }
    }
  });
  if (window.verseviewDesktop) {
    const updateBackend = value => { backend = value; root.dispatchEvent(new Event('preview:backend')); };
    window.verseviewDesktop.onBackendChanged(updateBackend);
    window.verseviewDesktop.backendState().then(updateBackend).catch(() => {});
    const updateObserver = value => { observer = value; root.dispatchEvent(new Event('preview:observer')); };
    window.verseviewDesktop.onObserverChanged(updateObserver);
    window.verseviewDesktop.observer().then(updateObserver).catch(() => {
      updateObserver({ connection: 'unavailable', message: 'Observer connection unavailable', sources: [], session: null });
    });
    window.verseviewDesktop.onAppearanceChanged(value => {
      if (value.theme === appliedTheme) applyAppearance(value);
    });
    window.verseviewDesktop.environment().then(value => {
      environment = value;
      root.dataset.platform = value.platform;
      if (value.appearance?.theme === appliedTheme) applyAppearance(value.appearance);
      root.dispatchEvent(new CustomEvent('preview:environment', { detail: environment }));
    }).catch(() => {});
  }
})();
