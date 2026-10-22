/* Shared typed settings boundary for the renderer and Electron main process. */
(function (root) {
  'use strict';
  const cloud = typeof module !== 'undefined' && module.exports ? require('./cloud-policy.js') : root.cloudPolicy;
  const session = typeof module !== 'undefined' && module.exports ? require('./session-policy.js') : root.sessionPolicy;
  const options = typeof module !== 'undefined' && module.exports ? require('./options-policy.js') : root.optionsPolicy;
  const languages = { English: 'en', Malayalam: 'ml', Hindi: 'hi', 'Multi-Language': 'multi' };
  const providers = { deepgram: 'Deepgram', sarvam: 'Sarvam AI', assemblyai_pro: 'AssemblyAI (Universal-3 Pro)',
    assemblyai_multilingual: 'AssemblyAI (Universal-3 Multilingual)', gladia: 'Gladia', gcp: 'Google Cloud STT', local_whisper: 'Local Whisper' };
  const bibles = ['KJV', 'WEB', 'ASV', 'NET', 'NLT', 'NIV', 'ESV', 'NASB', 'NKJV', 'AMP', 'CSB', 'MSG', 'OEB', 'WEBBE'];
  const detectionDefaults = {confidence: .75, manual_confirm: true, verify: true, verse_interrupt: false, spoken_numeral_mode: false, smart_amen: true, auto_save_notes: true};
  const watcherDefaults = {watcher_enabled:false,watcher_provider:'groq',watcher_batch_interval:5,watcher_auto_confidence:.85,watcher_passive_confidence:.60,watcher_window_lines:10,watcher_window_seconds:40,watcher_cooldown:60};
  const watcherProviders={groq:'Groq',cerebras:'Cerebras',mistral:'Mistral',local:'Local LLM'};
  const defaults={...detectionDefaults,...watcherDefaults,...session.defaults,...options.defaults};
  const fields = ['language', 'stt_engine', 'dual_stt_enabled', 'secondary_language', 'secondary_stt_engine', 'mic_index', 'remote_url', 'bible_translation', ...Object.keys(defaults)];
  function providersFor(language) {
    const allowed = ['deepgram', 'gladia', 'gcp', 'local_whisper'];
    if (['ml', 'hi'].includes(language)) allowed.splice(1, 0, 'sarvam');
    if (language === 'ml') allowed.splice(0, 1);
    if (language === 'en') allowed.splice(1, 0, 'assemblyai_pro', 'assemblyai_multilingual');
    if (language === 'multi') allowed.splice(1, 0, 'assemblyai_multilingual');
    return allowed;
  }
  function validField(key, value) {
    if(Object.hasOwn(options.defaults,key))return options.valid(key,value);
    if(Object.hasOwn(session.defaults,key))return session.valid(key,value);
    if(key==='watcher_enabled')return typeof value==='boolean';
    if(key==='watcher_provider')return typeof value==='string'&&Object.hasOwn(watcherProviders,value);
    if(Object.hasOwn(watcherDefaults,key)){
      const bounds={watcher_batch_interval:[1,300],watcher_auto_confidence:[0,1],watcher_passive_confidence:[0,1],watcher_window_lines:[1,100],watcher_window_seconds:[5,600],watcher_cooldown:[0,3600]};
      const [low,high]=bounds[key];
      return typeof value==='number'&&Number.isFinite(value)&&value>=low&&value<=high&&(!['watcher_window_lines','watcher_window_seconds','watcher_cooldown'].includes(key)||Number.isInteger(value));
    }
    if (key === 'confidence') return typeof value === 'number' && Number.isFinite(value) && value >= .5 && value <= 1;
    if (Object.hasOwn(detectionDefaults, key)) return typeof value === 'boolean';
    if (key === 'language') return typeof value === 'string' && Object.hasOwn(languages, value);
    if (['stt_engine', 'secondary_stt_engine'].includes(key)) return typeof value === 'string' && Object.hasOwn(providers, value);
    if (key === 'dual_stt_enabled') return typeof value === 'boolean';
    if (key === 'secondary_language') return value === null || ['en', 'ml', 'hi'].includes(value);
    if (key === 'mic_index') return Number.isSafeInteger(value) && value >= 0;
    if (key === 'remote_url') {
      if (typeof value !== 'string' || value.length > 512 || /[\s\x00-\x1f\x7f]/.test(value)) return false;
      try { const url = new URL(value); return ['http:', 'https:'].includes(url.protocol) && !!url.hostname
        && !url.username && !url.password && !url.search && !url.hash && (!url.port || Number(url.port) > 0); } catch { return false; }
    }
    return key === 'bible_translation' && bibles.includes(value);
  }
  function validatePatch(value) {
    if(value&&Object.keys(value).length===1&&Object.hasOwn(value,'connection_secrets'))return {connection_secrets:options.validateSecrets(value.connection_secrets)};
    if (value && Object.keys(value).length === 1 && Object.hasOwn(value, 'cloud_settings')) return {cloud_settings: cloud.validate(value.cloud_settings)};
    if (!value || typeof value !== 'object' || Array.isArray(value) || !Object.keys(value).length
      || Object.keys(value).some(key => !fields.includes(key) || !validField(key, value[key]))) throw new Error('Invalid settings changes');
    return Object.fromEntries(Object.entries(value));
  }
  function decode(value) {
    if (!value || !/^[a-f0-9]{32}$/.test(value.revision) || !value.values || !Array.isArray(value.devices)) return null;
    const values = {};
    for (const key of fields) {
      const item = value.values[key] ?? defaults[key];
      // Invalid legacy values stay empty so the user can correct them without exporting arbitrary text.
      values[key] = validField(key, item) ? item : Object.hasOwn(defaults, key) ? defaults[key] : key === 'mic_index' ? -1 : key === 'secondary_language' ? null : key === 'dual_stt_enabled' ? false : '';
    }
    return { revision: value.revision, values, cloud: cloud.decode(value.cloud), devices: value.devices.slice(0, 256)
      .filter(item => item && Number.isSafeInteger(item.id) && item.id >= 0 && typeof item.label === 'string')
      .map(item => ({ id: item.id, label: item.label.slice(0, 160) })) };
  }
  const api = Object.freeze({ languages, providers, bibles, fields, watcherProviders, providersFor, validatePatch, decode });
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.settingsPolicy = api;
})(globalThis);
