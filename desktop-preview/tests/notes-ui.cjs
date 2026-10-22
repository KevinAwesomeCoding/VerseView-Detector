'use strict';
// Packaged notes acceptance: synthetic speech/model/controller; no live services.
const {_electron}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const root=path.resolve(__dirname,'..'),out=path.join(root,'test-results','sermon-notes');fs.mkdirSync(out,{recursive:true});
(async()=>{
 const temp=fs.mkdtempSync(path.join(os.tmpdir(),'vv-notes-ui-')),source=path.join(temp,'source'),tag=`notes-${process.pid}`;fs.mkdirSync(source);
 const original={language:'English',stt_engine:'deepgram',mic_index:0,deepgram_api_key:'SECRET-SYNTHETIC',sarvam_api_key:'SECRET-SYNTHETIC',
  dual_stt_enabled:true,secondary_language:'ml',secondary_stt_engine:'sarvam',manual_confirm:true,verify:false,llm_enabled:false,
  auto_save_notes:false,auto_start:false,watcher_enabled:false,settings_sync_url:'',qa_notes_fixture:true};
 fs.writeFileSync(path.join(source,'settings.json'),JSON.stringify(original));
 let app,page,profile,backend;const checks=[],errors=[];let layouts=0;
 const visible=selector=>page.locator(selector).filter({visible:true}),state=()=>page.evaluate(()=>window.previewShell.getObserver().session);
 const navigate=view=>visible(`[aria-label="Dashboard navigation"] [data-action="view"][data-view="${view}"]`).click();
 const ready=(fn,arg=null)=>page.waitForFunction(fn,arg,{timeout:30000});
 const notes=()=>page.locator('.vv-notes');
 async function start(){
  await visible('[data-consumer-prepare="start"]').click();await ready(()=>window.previewShell.getObserver().session?.control?.state==='running');
  await page.locator('[data-engine-action="reject"]').filter({visible:true}).first().waitFor({timeout:30000});
  await page.locator('[data-engine-action="reject"]').filter({visible:true}).first().click();
 }
 async function prepare(kind){await page.locator('[data-notes-export-kind]').selectOption(kind);await page.locator('[data-notes="prepare-export"]').click();await ready(()=>Boolean(window.previewShell.getObserver().session?.control?.notes.export));}
 async function saveExport(destination,cancel=false){
  await app.evaluate(({dialog},{destination,cancel})=>{global.__notesSaveDialog=dialog.showSaveDialog;dialog.showSaveDialog=async()=>cancel?{canceled:true}:{filePath:destination};},{destination,cancel});
  try{await page.locator('[data-notes="save-export"]').click();await ready(()=>document.querySelector('.vv-notes [role="status"]').textContent.includes('Saved captured')||document.querySelector('.vv-notes [role="status"]').textContent.includes('Export cancelled'));}
  finally{await app.evaluate(({dialog})=>{dialog.showSaveDialog=global.__notesSaveDialog;delete global.__notesSaveDialog;});}
 }
 try{
  app=await _electron.launch({executablePath:process.env.PREVIEW_EXECUTABLE||require('electron'),args:process.env.PREVIEW_EXECUTABLE?[]:[root],env:{...process.env,VV_PREVIEW_TEST_PROFILE:'1',VV_PREVIEW_TEST_PROFILE_TAG:tag,VV_BACKEND_VERIFY:'1',VV_BACKEND_SOURCE_PROFILE:source,VV_OBSERVER_TEST_DIRECTORY:path.join(temp,'empty')}});
  page=await app.firstWindow();page.on('pageerror',e=>errors.push(e.message));profile=await app.evaluate(({app})=>app.getPath('userData'));assert.equal(path.basename(profile),tag);
  await page.locator('[data-consumer-prepare="settings"]').click();await ready(()=>Boolean(window.previewShell.getObserver().session?.control?.notes));
  backend=await page.evaluate(()=>window.previewShell.getBackend());assert.equal(backend.frozen,true);assert.equal(backend.verification,true);assert.equal(backend.guiImported,false);
  assert.equal(await visible('.vv-live-reference [data-view="notes"]').count(),1);
  await navigate('notes');await page.locator('[data-notes="generate"]').click();await ready(()=>document.querySelector('.vv-notes [role="status"]').textContent.includes('100 characters'));
  assert.equal((await state()).control.notes.text,'');await start();
  assert.ok((await state()).transcripts.some(r=>r.stream==='secondary'));
  await page.locator('[data-notes="generate"]').click();await ready(()=>window.previewShell.getObserver().session?.control?.notes.busy);
  assert.equal(await visible('[data-live-stop]').isEnabled(),true);await page.locator('[data-notes="cancel"]').click();
  await ready(()=>!window.previewShell.getObserver().session?.control?.notes.busy);assert.equal((await state()).control.notes.text,'');
  await page.locator('[data-notes="generate"]').click();await ready(()=>window.previewShell.getObserver().session?.control?.notes.status==='ready'&&!window.previewShell.getObserver().session?.control?.notes.busy);
  assert.match(await page.locator('.vv-notes-preview').innerText(),/SYNTHETIC SERMON NOTES/);assert.match(await page.locator('.vv-notes-preview').innerText(),/മലയാളം/);
  const preview=page.locator('.vv-notes-preview');await preview.focus();await page.keyboard.press('End');await page.keyboard.press('Control+End');await preview.evaluate(e=>e.scrollTop=e.scrollHeight);const scroll=await preview.evaluate(e=>({top:e.scrollTop,client:e.clientHeight,height:e.scrollHeight}));assert.ok(scroll.height>scroll.client*2&&scroll.top>0);assert.match(await preview.innerText(),/END OF SYNTHETIC NOTES/);await preview.evaluate(e=>e.scrollTop=0);assert.equal(await preview.evaluate(e=>e.scrollTop),0);checks.push('Long generated-note fixture scrolls independently from beginning to end and back with focusable preview');
  const first=(await state()).control.notes;checks.push('Empty input rejected; real frozen notes worker captures both original languages, cancellation discards late output, Stop remains usable, and generated notes show their snapshot/time/configured route');
  await prepare('all');const destination=path.join(temp,'captured-notes.txt');await saveExport(destination);
  const exported=fs.readFileSync(destination,'utf8');assert.ok(exported.length>6000);assert.match(exported,/ORIGINAL QA sermon speech/);assert.match(exported,/ദൈവത്തിന്റെ/);assert.match(exported,/John 3:16/);
  const cancelled=path.join(temp,'cancelled.txt');await saveExport(cancelled,true);assert.equal(fs.existsSync(cancelled),false);
  await page.screenshot({path:path.join(out,'notes-ready.png')});checks.push('Packaged trusted export IPC writes the exact complete Unicode packet at the chosen QA destination; cancellation leaves the destination absent (automated destination chooser, no live transcript)');
  await visible('[data-live-stop]').click();await ready(()=>window.previewShell.getObserver().session?.control?.state==='stopped');
  let n=(await state()).control.notes;assert.equal(n.auto.status,'transcript_saved');assert.equal(n.generated_at,first.generated_at);assert.match(fs.readFileSync(n.auto.transcript_path,'utf8'),/ദൈവത്തിന്റെ/);
  await navigate('settings');await page.locator('[data-detector-setting="auto_save_notes"]').check();await page.locator('[data-save-settings]').click();await ready(()=>window.previewShell.getObserver().session?.control?.settings.values.auto_save_notes===true);
  await navigate('notes');await start();await visible('[data-live-stop]').click();
  await ready(()=>window.previewShell.getObserver().session?.control?.state==='stopped'&&window.previewShell.getObserver().session?.control?.notes.auto.status==='saved'&&!window.previewShell.getObserver().session?.control?.notes.busy);
  n=(await state()).control.notes;assert.ok(fs.existsSync(n.auto.notes_path));assert.match(fs.readFileSync(n.auto.notes_path,'utf8'),/SYNTHETIC SERMON NOTES/);
  checks.push('Auto-save Off writes a bilingual transcript without another summary; Auto-save On persists the preference and writes transcript first, then completed notes, with visible time and locations');
  const textBefore=n.text,sessionBefore=(await state()).session_id;
  await page.locator('.vv-memory-tools summary').click();await page.locator('[data-notes="review-clear"]').click();
  const dialog=page.locator('.vv-memory-dialog');await dialog.waitFor();assert.match(await dialog.innerText(),/Saved sessions, exported files, credentials and diagnostic journals are retained/);
  await dialog.locator('[data-notes="close-review"]').click();assert.equal((await state()).control.notes.text,textBefore);
  await page.locator('[data-notes="review-clear"]').click();await dialog.waitFor();await dialog.locator('[data-notes="confirm-clear"]').click();
  await ready(id=>Boolean(window.previewShell.getObserver().session?.session_id&&window.previewShell.getObserver().session.session_id!==id),sessionBefore);
  let cleared=await state();assert.equal(cleared.control.notes.text,'');assert.equal(cleared.control.verses.context.book,'');assert.equal(cleared.transcripts.length,0);assert.equal(cleared.control.verses.history.length,0);
  assert.equal(cleared.control.settings.values.auto_save_notes,true);assert.ok(fs.existsSync(destination));
  const backup=cleared.control.operator.library.rows.find(r=>r.reason==='before memory clear');assert.ok(backup);
  assert.ok(fs.readdirSync(path.join(profile,'Backend','Diagnostics')).some(f=>f.startsWith('before-clear-')));
  await visible('[data-operator="open"]').click();await page.locator(`.vv-session-dialog [data-record="${backup.id}"]`).click();
  await ready(()=>Boolean(window.previewShell.getObserver().session?.control?.operator.library.selected));
  await page.locator('.vv-session-dialog [data-operator="resume"]').click();await ready(()=>window.previewShell.getObserver().session?.control?.recovery.status==='staged');await page.keyboard.press('Escape');
  await ready(()=>window.previewShell.getObserver().session?.control?.notes.text.length>0);assert.equal((await state()).control.state,'stopped');assert.equal((await state()).control.notes.text,textBefore);
  checks.push('Clear Memory has an explicit scoped Keep/Save-and-clear dialog; save succeeds before reset; both streams/context/history/notes reset, credentials and exports survive, diagnostics are archived, and Saved sessions restores full content and notes without starting speech');
  const settingsPath=path.join(profile,'Backend','settings.json');const values=JSON.parse(fs.readFileSync(settingsPath));fs.writeFileSync(settingsPath,JSON.stringify({...values,qa_notes_failure:true}));
  await page.locator('[data-notes="generate"]').click();await ready(()=>window.previewShell.getObserver().session?.control?.notes.status==='failed'&&!window.previewShell.getObserver().session?.control?.notes.busy);
  assert.equal((await state()).control.notes.text,textBefore);assert.equal(JSON.stringify(await state()).includes('SECRET-'),false);
  fs.writeFileSync(settingsPath,JSON.stringify(values));checks.push('A synthetic provider failure retains prior notes and snapshot, shows failure without leaking the provider exception, and does not retry');
  for(const width of [1180,900,660])for(const layout of ['studio','focus']){
   await app.evaluate(({BrowserWindow},w)=>BrowserWindow.getAllWindows()[0].setSize(w,720),width);await navigate('settings');await page.locator('[data-appearance-layout]').selectOption(layout);
   for(const theme of ['sage','midnight','glass','galaxy','aurora','ember']){
    await page.locator(`[data-theme-choice="${theme}"]`).click();await navigate('notes');
    const bounds=await page.locator('[data-layout]').evaluate(e=>({client:e.clientWidth,scroll:e.scrollWidth}));assert.ok(bounds.scroll<=bounds.client+1,JSON.stringify({width,layout,theme,bounds}));
    await page.locator('.vv-notes-preview').scrollIntoViewIfNeeded();assert.equal(await visible('[data-operator="emergency"]').isEnabled(),true);layouts++;await navigate('settings');
   }
  }
  await navigate('notes');await page.screenshot({path:path.join(out,'notes-narrow.png')});assert.deepEqual(errors,[]);
  const processInfo=await app.evaluate(({app})=>({packaged:app.isPackaged,executable:process.execPath,resources:process.resourcesPath}));
  const report={result:'PASS',testedAt:new Date().toISOString(),processInfo,backend,checks,layouts,exportedCharacters:exported.length,errors,microphoneSTT:'MOCKED QA callbacks',summaryProvider:'SYNTHETIC completion through real summary prompt',visibleVerseVIEW:'MOCKED controller',windowsPhysical:'UNVERIFIED'};
  fs.writeFileSync(path.join(out,'results.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));assert.deepEqual(JSON.parse(fs.readFileSync(path.join(source,'settings.json'))),original);
  if(process.env.VV_NOTES_INSPECT==='1'){
   await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].setSize(1180,820));await navigate('settings');await page.locator('[data-theme-choice="glass"]').click();await navigate('notes');
   await prepare('all');console.log(JSON.stringify({inspectionReady:true,nativeExportDirectory:temp,profile}));
   await new Promise(resolve=>{process.stdin.once('data',resolve);app.once('close',resolve);});process.stdin.pause();
   const native=path.join(temp,'Native Notes.txt');if(fs.existsSync(native)){const text=fs.readFileSync(native,'utf8');assert.match(text,/ORIGINAL QA sermon speech/);assert.match(text,/ദൈവത്തിന്റെ/);fs.writeFileSync(path.join(out,'native-export.json'),JSON.stringify({result:'PASS',path:native,characters:text.length,fullUnicode:true},null,2)+'\n');}
  }
 }catch(error){
  if(page){await page.screenshot({path:path.join(out,'failure.png')}).catch(()=>{});fs.writeFileSync(path.join(out,'failure-state.json'),JSON.stringify(await state().catch(()=>null),null,2));}
  if(profile&&path.basename(profile)===tag){
   const log=path.join(profile,'Backend','verseview.log');
   if(fs.existsSync(log))fs.writeFileSync(path.join(out,'failure-backend.log'),fs.readFileSync(log,'utf8').replaceAll('SECRET-SYNTHETIC','[QA credential]'));
   const directory=path.join(profile,'Backend','Observer');
   if(fs.existsSync(directory))for(const name of fs.readdirSync(directory).filter(n=>/^engine-\d+\.json$/.test(n)))fs.copyFileSync(path.join(directory,name),path.join(out,'failure-raw-feed.json'));
  }
  throw error;
 }
 finally{if(app)await app.close().catch(()=>{});if(profile&&path.basename(profile)===tag&&path.basename(path.dirname(profile))==='QA')fs.rmSync(profile,{recursive:true,force:true});fs.rmSync(temp,{recursive:true,force:true});}
})().catch(error=>{console.error(error);process.exitCode=1;});
