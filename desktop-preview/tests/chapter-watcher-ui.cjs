'use strict';
// Frozen application acceptance; synthetic mic/model/controller, never live services.
const {_electron}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const root=path.resolve(__dirname,'..'),out=path.join(root,'test-results','chapter-watcher');fs.mkdirSync(out,{recursive:true});
(async()=>{
 const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'vv-chapter-watcher-')),source=path.join(temporary,'source'),tag=`chapter-watcher-${process.pid}`;fs.mkdirSync(source);
 const original={language:'English',stt_engine:'deepgram',mic_index:0,deepgram_api_key:'SECRET-SYNTHETIC',sarvam_api_key:'SECRET-SYNTHETIC',
  dual_stt_enabled:true,secondary_language:'ml',secondary_stt_engine:'sarvam',manual_confirm:true,verify:false,llm_enabled:false,
  auto_save_notes:false,auto_start:false,watcher_enabled:false,watcher_provider:'local',local_llm_enabled:true,local_llm_model:'SYNTHETIC-MODEL',settings_sync_url:''};
 fs.writeFileSync(path.join(source,'settings.json'),JSON.stringify(original));
 let app,page,profile;const errors=[],checks=[];let layouts=0;
 const session=()=>page.evaluate(()=>window.previewShell.getObserver().session);
 const accepted=async refs=>(await session()).delivery_events.filter(e=>e.outcome==='COMMAND_ACCEPTED'&&(!refs||refs.includes(e.reference)));
 const visible=selector=>page.locator(selector).filter({visible:true});
 async function operator(action,payload={}){
  const result=await page.evaluate(async({action,payload})=>window.verseviewDesktop.operator(window.previewShell.getObserver().session.session_id,action,payload),{action,payload});
  await page.waitForFunction(id=>window.previewShell.getObserver().session.control.results.some(r=>r.id===id),result.id);
  return (await session()).control.results.find(r=>r.id===result.id);
 }
 try{
  app=await _electron.launch({executablePath:process.env.PREVIEW_EXECUTABLE||require('electron'),args:process.env.PREVIEW_EXECUTABLE?[]:[root],env:{...process.env,VV_PREVIEW_TEST_PROFILE:'1',VV_PREVIEW_TEST_PROFILE_TAG:tag,VV_BACKEND_VERIFY:'1',VV_BACKEND_SOURCE_PROFILE:source,VV_OBSERVER_TEST_DIRECTORY:path.join(temporary,'empty')}});
  page=await app.firstWindow();page.on('pageerror',e=>errors.push(e.message));profile=await app.evaluate(({app})=>app.getPath('userData'));assert.equal(path.basename(profile),tag);
  await page.locator('[data-consumer-prepare="settings"]').click();await page.waitForFunction(()=>window.previewShell.getObserver().session?.control?.verses,{timeout:30000});
  const backend=await page.evaluate(()=>window.previewShell.getBackend());assert.equal(backend.frozen,true);assert.equal(backend.verification,true);assert.equal(backend.guiImported,false);
  await visible('[data-action="view"][data-view="settings"]').click();
  const watcher=page.locator('[data-detector-setting="watcher_enabled"]');assert.equal(await watcher.isChecked(),false);
  assert.equal(await page.locator('[data-detector-setting="watcher_provider"]').inputValue(),'local');
  assert.equal(await page.locator('[data-detector-setting="watcher_batch_interval"]').count(),0,'Tuning must be hidden outside Developer Mode');
  await watcher.check();await page.locator('[data-save-settings]').click();await page.waitForFunction(()=>window.previewShell.getObserver().session.control.settings.values.watcher_enabled===true);
  await visible('[data-action="view"][data-view="session"]').click();
  await operator('set_context',{reference:'John 3:17',context_revision:(await session()).control.verses.context.revision});
  let grid=page.locator('.vv-live-reference [data-grid-session]');await grid.locator('summary').click();
  assert.equal(await grid.locator('.vv-chapter-grid button').count(),36);assert.equal(await grid.locator('[aria-current="true"]').innerText(),'17');
  const staleGrid=(await session()).control.verses.grid;
  await grid.getByRole('button',{name:'Preview John 3:36',exact:true}).click();
  await page.waitForFunction(()=>window.previewShell.getObserver().session.control.verses.selected?.reference==='John 3:36'&&window.previewShell.getObserver().session.control.verses.selected?.status==='ready');
  assert.equal(await grid.evaluate(e=>e.open),true);assert.equal((await accepted()).length,0);
  await operator('set_context',{reference:'John 4',context_revision:(await session()).control.verses.context.revision});
  assert.equal((await operator('grid_preview',{reference:'John 3:36',context_revision:staleGrid.revision})).outcome,'rejected');
  assert.equal((await session()).control.verses.grid.count,54);
  await operator('set_context',{reference:'John 3',context_revision:(await session()).control.verses.context.revision});
  checks.push('Off watcher remains configurable; technical tuning is hidden in consumer mode; John 3 has 36 local buttons and current-context highlighting; preview is read-only and stale grid clicks are rejected');
  await visible('[data-consumer-prepare="start"]').click();
  const reject=page.locator('[data-engine-action="reject"]').filter({visible:true});await reject.first().waitFor({timeout:30000});await reject.first().click();
  await page.waitForFunction(()=>window.previewShell.getObserver().session.control.suggestions.rows.length===2,{timeout:30000});
  let snapshot=await session();assert.deepEqual(new Set(snapshot.control.suggestions.rows.map(r=>r.stream)),new Set(['primary','secondary']));
  assert.ok(snapshot.control.suggestions.rows.some(r=>r.confidence===.95));assert.equal((await accepted(['John 3:19','John 3:20'])).length,0);
  assert.equal(snapshot.control.suggestions.phase,'suggested');
  const panel=page.locator('[data-suggestion-panel]');await panel.locator('summary').click();
  const english=snapshot.control.suggestions.rows.find(r=>r.stream==='primary');
  await page.locator(`[data-suggestion-preview="${english.id}"]`).click();
  const dialog=page.locator('.vv-verse-dialog');await dialog.waitFor();await page.waitForFunction(()=>window.previewShell.getObserver().session.control.verses.selected?.reference==='John 3:19'&&window.previewShell.getObserver().session.control.verses.selected?.status==='ready');
  assert.equal((await accepted(['John 3:19','John 3:20'])).length,0);await page.keyboard.press('Escape');
  await page.screenshot({path:path.join(out,'watcher-ready.png')});
  await page.waitForFunction(()=>{const events=window.previewShell.getObserver().session.delivery_events.filter(e=>e.outcome==='COMMAND_ACCEPTED');return events.length&&Date.now()-Date.parse(events.at(-1).timestamp)>3500;});
  await page.locator(`[data-suggestion-id="${english.id}"]`).click();
  // No bypass: wait for an acknowledged guarded result, including cooldown suppression.
  await page.waitForFunction(id=>window.previewShell.getObserver().session.control.suggestions.rows.some(r=>r.id===id&&['accepted','review'].includes(r.state)),english.id);
  snapshot=await session();const sent=snapshot.control.suggestions.rows.find(r=>r.id===english.id);
  const delivery=snapshot.delivery_events.filter(e=>e.candidate_id===sent.candidate_id);assert.ok(delivery.length);assert.ok(delivery.some(e=>e.source==='WATCHER-MANUAL'));
  assert.equal(sent.state,'accepted');assert.ok(delivery.some(e=>e.outcome==='COMMAND_ACCEPTED'));
  assert.match(await page.locator('[data-suggestion-panel]').innerText(),/visible output unverified/);
  await assert.rejects(page.evaluate(async id=>window.verseviewDesktop.sendSuggestion(window.previewShell.getObserver().session.session_id,id),english.id));
  const ml=snapshot.control.suggestions.rows.find(r=>r.stream==='secondary');await page.locator(`[data-review-suggestion="${ml.id}"]`).click();
  await page.waitForFunction(id=>!window.previewShell.getObserver().session.control.suggestions.rows.some(r=>r.id===id),ml.id);
  const oldRevision=snapshot.control.suggestions.revision;
  assert.equal((await operator('clear_suggestions',{revision:oldRevision})).outcome,'rejected');
  await page.locator('[data-engine-action="clear_suggestions"]').click();await page.waitForFunction(()=>window.previewShell.getObserver().session.control.suggestions.rows.length===0);
  assert.equal((await accepted(['John 3:20'])).length,0);
  checks.push('Actual frozen bilingual watcher processes synthetic .95 English and .70 Malayalam replies without presenting either; Preview is read-only; Display correlates guarded events to a candidate; Dismiss, revision-checked Clear and repeated-send rejection work');
  const beforeHistory=await session(),countBefore=(await accepted()).length;
  await page.locator('.vv-live-reference [data-verse="open"]').click();await dialog.locator('[data-tab="history"]').click();
  assert.ok(beforeHistory.control.verses.history.length>0);await dialog.locator('[data-verse="clear-history"]').click();
  await page.waitForFunction(()=>window.previewShell.getObserver().session.control.verses.history.length===0);
  assert.equal((await accepted()).length,countBefore);assert.deepEqual((await session()).control.verses.context,beforeHistory.control.verses.context);
  await page.keyboard.press('Escape');checks.push('Clear current history empties its list while accepted delivery evidence and the current context remain intact');
  for(const width of [1180,900,660])for(const layout of ['studio','focus']){
   await app.evaluate(({BrowserWindow},width)=>BrowserWindow.getAllWindows()[0].setSize(width,720),width);
   await visible('[data-action="view"][data-view="settings"]').click();await page.locator('[data-appearance-layout]').selectOption(layout);
   for(const theme of ['sage','midnight','glass','galaxy','aurora','ember']){
    await page.locator(`[data-theme-choice="${theme}"]`).click();await visible('[data-action="view"][data-view="session"]').click();
    grid=page.locator('.vv-live-reference [data-grid-session]');if(!await grid.evaluate(e=>e.open))await grid.locator('summary').click();
    const bounds=await page.locator('[data-layout]').evaluate(e=>({client:e.clientWidth,scroll:e.scrollWidth}));assert.ok(bounds.scroll<=bounds.client+1,JSON.stringify({width,layout,theme,bounds}));
    await grid.locator('.vv-chapter-grid button').last().scrollIntoViewIfNeeded();assert.equal(await grid.locator('.vv-chapter-grid button').last().isVisible(),true);
    assert.equal(await visible('[data-operator="emergency"]').isEnabled(),true);layouts++;
    await visible('[data-action="view"][data-view="settings"]').click();
   }
  }
  await visible('[data-action="view"][data-view="session"]').click();await page.screenshot({path:path.join(out,'chapter-narrow.png')});
  await visible('[data-live-stop]').click();await page.waitForFunction(()=>window.previewShell.getObserver().session.control.state==='stopped');
  assert.deepEqual(errors,[]);assert.equal(JSON.stringify(await session()).includes('SECRET-'),false);
  const processInfo=await app.evaluate(({app})=>({executable:process.execPath,packaged:app.isPackaged,resources:process.resourcesPath}));
  checks.push(`${layouts} width/layout/theme cases fit; final verse numbers remain scrollable and emergency remains usable`);
  fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({result:'PASS',testedAt:new Date().toISOString(),processInfo,backend,checks,layouts,delivery,errors,microphoneSTT:'MOCKED QA callbacks',models:'SYNTHETIC replies',visibleVerseVIEW:'MOCKED controller',windowsPhysical:'UNVERIFIED'},null,2)+'\n');console.log(JSON.stringify({result:'PASS',processInfo,checks,layouts,delivery},null,2));
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(source,'settings.json'))),original);
  if(process.env.VV_CHAPTER_INSPECT==='1'){
   await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].setSize(1180,820));
   await visible('[data-action="view"][data-view="settings"]').click();await page.locator('[data-theme-choice="glass"]').click();
   await visible('[data-action="view"][data-view="session"]').click();grid=page.locator('.vv-live-reference [data-grid-session]');if(!await grid.evaluate(e=>e.open))await grid.locator('summary').click();
   await new Promise(resolve=>{process.stdin.once('data',resolve);app.once('close',resolve);});process.stdin.pause();
  }
 }catch(error){if(page){await page.screenshot({path:path.join(out,'failure.png')}).catch(()=>{});fs.writeFileSync(path.join(out,'failure-state.json'),JSON.stringify(await session().catch(()=>null),null,2));}throw error;}
 finally{if(app)await app.close().catch(()=>{});if(profile&&path.basename(profile)===tag&&path.basename(path.dirname(profile))==='QA')fs.rmSync(profile,{recursive:true,force:true});fs.rmSync(temporary,{recursive:true,force:true});}
})().catch(error=>{console.error(error);process.exitCode=1;});
