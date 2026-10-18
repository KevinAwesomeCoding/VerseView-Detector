'use strict';
const fs = require('node:fs');
const path = require('node:path');
const settingsPolicy = require('./src/settings-policy.js');

const MAX_BYTES = 2 * 1024 * 1024;
const FRESH_MS = 6000;
const text = (value, limit = 2000) => typeof value === 'string' ? value.slice(0, limit) : '';
const timestamp = value => typeof value === 'string' && Number.isFinite(Date.parse(value)) ? value : null;
const role = value => ['primary', 'secondary'].includes(value) ? value : 'unknown';

function feedDirectory({ platform, appData, home }) {
  const paths = platform === 'win32' ? path.win32 : path.posix;
  return platform === 'linux' ? paths.join(home, '.verseview', 'Observer') : paths.join(appData, 'VerseView', 'Observer');
}

function decodeControl(value) {
  if (!value || !/^[a-f0-9]{32}$/.test(value.id) || !['stopped', 'starting', 'running', 'stopping', 'closed'].includes(value.state)) return null;
  return { id: value.id, state: value.state,
    actions: Array.isArray(value.actions) ? value.actions.filter(action => ['start', 'stop', 'save_settings', 'panic', 'restore_session', 'discard_session', 'send_suggestion', 'edit_outline'].includes(action)) : [],
    recovery: decodeRecovery(value.recovery),
    suggestions: decodeSuggestions(value.suggestions),
    outline:decodeOutline(value.outline),
    settings: settingsPolicy.decode(value.settings),
    pending: (Array.isArray(value.pending) ? value.pending : []).slice(0, 16)
      .filter(item => item && text(item.candidate_id, 128) && text(item.reference, 128))
      .map(item => ({ candidate_id: text(item.candidate_id, 128), reference: text(item.reference, 128),
        confidence: Number.isFinite(item.confidence) ? Math.max(0, Math.min(1, item.confidence)) : 0,
        source: text(item.source, 64), stream: role(item.stream) })),
    results: (Array.isArray(value.results) ? value.results : []).slice(-32)
      .filter(item => item && /^[a-f0-9]{32}$/.test(item.id))
      .map(item => ({ id: item.id, action: text(item.action, 16), outcome: text(item.outcome, 24), reason: text(item.reason, 200) })) };
}

function decodeOutline(value){
  if(!value||!/^[a-f0-9]{32}$/.test(value.revision||'')||typeof value.text!=='string'||value.text.length>4000)return null;
  return {revision:value.revision,text:value.text,source:['manual','model'].includes(value.source)?value.source:'',
    updated_at:timestamp(value.updated_at),enabled:value.enabled===true,active:value.active===true,
    provider_ready:value.provider_ready===true,status:['idle','waiting','generating','error','edited','updated','stopped'].includes(value.status)?value.status:'idle',
    message:text(value.message,400)};
}

function decodeSuggestions(value) {
  if (!value || typeof value.enabled !== 'boolean') return null;
  const count = key => Number.isSafeInteger(value[key]) ? Math.max(0, Math.min(1000000, value[key])) : 0;
  return {enabled:value.enabled,active:value.active === true,has_clients:value.has_clients === true,busy:value.busy === true,
    cycles:count('cycles'),suggested:count('suggested'),discarded:count('discarded'),
    rows:(Array.isArray(value.rows) ? value.rows : []).slice(-6)
      .filter(row => row && /^[a-f0-9]{32}$/.test(row.id || '') && text(row.reference,128) && timestamp(row.created_at)
        && ['auto_suggest','passive_suggest'].includes(row.kind) && ['available','sending','accepted','review','unknown'].includes(row.state))
      .map(row => ({id:row.id,reference:text(row.reference,128),created_at:row.created_at,kind:row.kind,state:row.state,
        confidence:Number.isFinite(row.confidence) ? Math.min(1,Math.max(0,row.confidence)) : 0,
        candidate_id:/^[a-f0-9]{32}$/.test(row.candidate_id || '') ? row.candidate_id : null,
        stream:role(row.stream),language:['en','ml','hi','multi'].includes(row.language) ? row.language : 'und',
        reasoning:text(row.reasoning,400)}))};
}

function decodeRecovery(value) {
  if (!value || !['none', 'available', 'staged', 'invalid', 'saved'].includes(value.status)) return null;
  const preview = value.preview;
  const language = role => ['en', 'ml', 'hi', 'multi'].includes(preview?.languages?.[role]) ? preview.languages[role] : 'und';
  return { status: value.status, revision: /^[a-f0-9]{32}$/.test(value.revision || '') ? value.revision : null,
    message: text(value.message, 400), saved_at: timestamp(value.saved_at), reason: text(value.reason, 32),
    verse_count: Number.isSafeInteger(value.verse_count) ? Math.max(0, Math.min(4096, value.verse_count)) : 0,
    preview: preview && ['available', 'staged'].includes(value.status) ? {
      primary: text(preview.primary, 2000), secondary: text(preview.secondary, 2000),
      languages: { primary: language('primary'), secondary: language('secondary') },
      sources: { primary: preview.sources?.primary === 'speech' ? 'speech' : 'context',
        secondary: preview.sources?.secondary === 'speech' ? 'speech' : 'context' },
      references: Array.isArray(preview.references) ? preview.references.slice(-10).map(ref => text(ref, 128)) : [] } : null };
}

function decodeSnapshot(value, now = Date.now()) {
  if (!value || value.schema !== 1 || !/^[a-f0-9]{32}$/.test(value.session_id)
    || !Number.isSafeInteger(value.pid) || value.pid <= 0 || !Number.isSafeInteger(value.revision) || value.revision < 0
    || !['engine', 'callback-replay'].includes(value.origin) || !timestamp(value.updated_at)
    || Date.parse(value.updated_at) > now + 10000 || !timestamp(value.started_at)
    || !Array.isArray(value.transcripts) || !Array.isArray(value.delivery_events) || !value.config?.streams) {
    throw new Error('Unsupported observer snapshot');
  }
  const config = { bible_translation: text(value.config.bible_translation, 64), streams: {} };
  const streams = {};
  for (const stream of ['primary', 'secondary']) {
    const item = value.config.streams[stream];
    if (!item || typeof item.enabled !== 'boolean') throw new Error('Invalid stream configuration');
    config.streams[stream] = { language: text(item.language, 24), provider: text(item.provider, 64), enabled: item.enabled };
    streams[stream] = { state: text(value.streams?.[stream]?.state, 64),
      last_transcript_at: timestamp(value.streams?.[stream]?.last_transcript_at) };
  }
  const transcripts = value.transcripts.slice(-48).filter(item => item && timestamp(item.timestamp) && text(item.text))
    .map(item => ({ id: text(item.id, 128), stream: role(item.stream), timestamp: item.timestamp,
      language: text(item.language, 24), provider: text(item.provider, 64), text: text(item.text),
      translation: text(item.translation), is_final: item.is_final === true }));
  const delivery_events = value.delivery_events.slice(-192).filter(item => item && text(item.candidate_id) && timestamp(item.timestamp))
    .map(item => ({ candidate_id: text(item.candidate_id, 128), reference: text(item.reference, 128),
      stream: role(item.stream), language: text(item.language, 24), source: text(item.source, 64),
      timestamp: item.timestamp, stage: text(item.stage, 64), outcome: text(item.outcome, 64), reason: text(item.reason, 400) }));
  return { schema: 1, session_id: value.session_id, pid: value.pid, origin: value.origin,
    started_at: value.started_at, updated_at: value.updated_at, revision: value.revision,
    host: value.host?.managed === true ? { managed: true, verification: value.host.verification === true,
      notice: text(value.host.notice, 500), warmup: decodeWarmup(value.host.warmup) } : null,
    engine_state: text(value.engine_state, 64), config, streams, transcripts, delivery_events, control: decodeControl(value.control) };
}

function decodeWarmup(value) {
  if (!value || !['off', 'skipped', 'running', 'complete', 'failed', 'cancelled', 'busy'].includes(value.status)) return null;
  return { status: value.status, total: Number.isSafeInteger(value.total) ? Math.min(4, Math.max(0, value.total)) : 0,
    roles: (Array.isArray(value.roles) ? value.roles : []).slice(0, 4)
      .filter(row => row && ['verse', 'outline', 'summary', 'watcher'].includes(row.role) && ['warmed', 'failed'].includes(row.status))
      .map(row => ({ role: row.role, status: row.status,
        elapsed_seconds: Number.isFinite(row.elapsed_seconds) ? Math.min(86400, Math.max(0, row.elapsed_seconds)) : 0 })) };
}

class EngineFeedReader {
  constructor({ directory, onChange = () => {}, clock = Date.now, interval = 750 }) {
    this.directory = directory;
    this.onChange = onChange;
    this.clock = clock;
    this.interval = interval;
    this.selected = null;
    this.snapshot = { connection: 'waiting', message: 'Waiting for an observer-enabled detector', sources: [], session: null };
    this.signature = '';
    this.cache = new Map();
  }

  select(sessionId) {
    if (sessionId !== null && (!/^[a-f0-9]{32}$/.test(sessionId) || !this.snapshot.sources.some(source => source.session_id === sessionId))) {
      throw new Error('Unknown observer session');
    }
    this.selected = sessionId;
    return this.poll();
  }

  async readFile(name) {
    const handle = await fs.promises.open(path.join(this.directory, name), fs.constants.O_RDONLY | (fs.constants.O_NOFOLLOW || 0));
    try {
      const stat = await handle.stat();
      if (!stat.isFile() || stat.size > MAX_BYTES) throw new Error('Invalid snapshot size');
      const data = await handle.readFile({ encoding: 'utf8' });
      if (Buffer.byteLength(data) > MAX_BYTES) throw new Error('Invalid snapshot size');
      const snapshot = decodeSnapshot(JSON.parse(data), this.clock());
      if (name !== `engine-${snapshot.pid}.json`) throw new Error('Observer process mismatch');
      return snapshot;
    } finally { await handle.close(); }
  }

  async poll() {
    if (this.pending) { await this.pending; return this.snapshot; }
    this.pending = this.scan();
    try { await this.pending; return this.snapshot; } finally { this.pending = null; }
  }

  async scan() {
    let sessions = [], invalid = 0;
    try {
      const entries = (await fs.promises.readdir(this.directory, { withFileTypes: true }))
        .filter(entry => entry.isFile() && /^engine-[0-9]+\.json$/.test(entry.name));
      // Old process snapshots must not prevent a later detector launch from connecting.
      const dated = await Promise.allSettled(entries.map(async entry => ({ name: entry.name,
        stat: await fs.promises.stat(path.join(this.directory, entry.name)) })));
      const recent = dated.filter(result => result.status === 'fulfilled').map(result => result.value)
        .sort((left, right) => right.stat.mtimeMs - left.stat.mtimeMs).slice(0, 32);
      const names = new Set(recent.map(entry => entry.name));
      for (const name of this.cache.keys()) if (!names.has(name)) this.cache.delete(name);
      const results = await Promise.allSettled(recent.map(async entry => {
        const key = `${entry.stat.mtimeMs}:${entry.stat.size}:${entry.stat.ino}`;
        const cached = this.cache.get(entry.name);
        if (cached?.key === key) return cached.snapshot;
        const snapshot = await this.readFile(entry.name);
        this.cache.set(entry.name, { key, snapshot });
        return snapshot;
      }));
      sessions = results.filter(result => result.status === 'fulfilled').map(result => result.value);
      invalid = results.length - sessions.length;
    } catch (error) {
      if (error.code !== 'ENOENT') invalid++;
    }
    sessions.sort((left, right) => Date.parse(right.updated_at) - Date.parse(left.updated_at));
    const fresh = session => this.clock() - Date.parse(session.updated_at) <= FRESH_MS;
    const active = sessions.filter(fresh);
    // Follow only the session change caused by our own acknowledged Start request.
    const transition = this.commandTransition;
    if (transition) {
      const replacement = sessions.find(item => item.pid === transition.pid && item.control?.id === transition.controlId
        && item.control.results.some(result => result.id === transition.id && result.outcome === 'requested'));
      if (replacement) {
        if (this.selected === transition.sessionId) this.selected = replacement.session_id;
        this.commandTransition = null;
      } else if (this.clock() > transition.deadline) this.commandTransition = null;
    }

    const sources = sessions.map(session => ({ session_id: session.session_id, pid: session.pid, origin: session.origin,
      fresh: fresh(session), engine_state: session.engine_state })).sort((left, right) => left.pid - right.pid);
    let session = this.selected ? sessions.find(item => item.session_id === this.selected) : null;
    let connection, message;
    if (this.selected && !session) {
      connection = 'unavailable'; message = 'The selected detector feed is unavailable';
    } else if (!this.selected && active.length > 1) {
      connection = 'ambiguous'; message = 'Several detector feeds are active; choose a process';
    } else {
      session ||= active[0] || sessions[0] || null;
      connection = session ? (fresh(session) ? 'connected' : 'stale') : (invalid ? 'invalid' : 'waiting');
      message = ({ connected: 'Local observer feed connected', stale: 'Feed is stale; showing the last snapshot',
        invalid: 'Observer snapshot could not be read', waiting: 'Waiting for an observer-enabled detector' })[connection];
    }
    this.snapshot = { connection, message, selected: this.selected, sources, session: session || null };
    const signature = JSON.stringify({ connection, selected: this.selected,
      sources, session: session && [session.session_id, session.revision] });
    if (signature !== this.signature) {
      this.signature = signature;
      this.onChange(this.snapshot);
    }
  }

  start() {
    if (this.timer) return;
    this.poll();
    this.timer = setInterval(() => this.poll(), this.interval);
    this.timer.unref();
  }

  stop() { clearInterval(this.timer); this.timer = null; }
}

module.exports = { EngineFeedReader, decodeSnapshot, feedDirectory, FRESH_MS };
