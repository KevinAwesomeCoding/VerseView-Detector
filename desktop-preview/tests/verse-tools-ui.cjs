'use strict';
// QA fixtures and fake controller only. This is not microphone or visible-output acceptance.
const {_electron}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),out=path.join(root,'test-results');fs.mkdirSync(out,{recursive:true});
const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'vv-verse-ui-')),source=path.join(tmp,'source');fs.mkdirSync(source);
fs.writeFileSync(path.join(source,'settings.json'),JSON.stringify({language:'English',stt_engine:'deepgram',deepgram_api_key:'SYNTHETIC-ONLY',mic_index:0,remote_url:'http://127.0.0.1:50010/control.html',bible_translation:'KJV',confidence:.75,manual_confirm:true,verify:false,cooldown:3,dedup_window:60,llm_enabled:false,auto_save_notes:false,auto_start:false,settings_sync_url:''}));
(async()=>{
 let app,page,qaProfile;const tag=`verse-tools-${process.pid}`,checks=[],errors=[];
 try{
  app=await _electron.launch({executablePath:process.env.PREVIEW_EXECUTABLE||require('electron'),args:process.env.PREVIEW_EXECUTABLE?[]:[root],env:{...process.env,VV_PREVIEW_TEST_PROFILE:'1',VV_PREVIEW_TEST_PROFILE_TAG:tag,VV_BACKEND_VERIFY:'1',VV_BACKEND_SOURCE_PROFILE:source,VV_OBSERVER_TEST_DIRECTORY:path.join(tmp,'empty')}});
  page=await app.firstWindow();page.on('pageerror',e=>errors.push(e.message));
  qaProfile=await app.evaluate(({app})=>app.getPath('userData'));assert.equal(path.basename(qaProfile),tag);const profile=path.join(qaProfile,'Backend');assert.equal(fs.existsSync(profile),false,'Clean only a closed, confirmed synthetic QA profile before running');
  await page.evaluate(()=>localStorage.clear());await page.reload();await page.locator('[data-consumer-prepare="settings"]').click();
  await page.waitForFunction(()=>window.previewShell.getObserver().session?.control?.verses,{timeout:30000});
  const backend=await page.evaluate(()=>window.previewShell.getBackend());assert.equal(backend.frozen,true);assert.equal(backend.verification,true);assert.equal(backend.guiImported,false);
  const d=page.locator('.vv-verse-dialog'),click=a=>d.locator(`[data-verse="${a}"]`).click(),tab=a=>d.locator(`[data-tab="${a}"]`).click();
  const open=()=>page.locator('[data-verse="open"]').click();
  const count=()=>page.evaluate(()=>window.previewShell.getObserver().session.delivery_events.filter(e=>e.outcome==='COMMAND_ACCEPTED').length);
  const preview=async ref=>{if(await d.isVisible())await click('close');const live=page.locator('.vv-live-reference');await live.locator('[data-verse-field="reference"]').fill(ref);await live.locator('[data-verse-form="preview"] button').click();await page.waitForFunction(r=>{const v=window.previewShell.getObserver().session.control.verses;return v.selected?.reference===r&&v.selected.status==='ready';},ref);await open();};
  const context=async ref=>{await tab('context');await click('reload');await d.locator('[data-verse-field="context"]').fill(ref);await d.locator('[data-verse-form="context"] button[type="submit"]').click();};
  await open();await preview('John 3:21');assert.match(await d.locator('.vv-verse-text').innerText(),/QA fixture KJV/);assert.equal(await d.locator('[data-verse="send"]').isEnabled(),false);assert.equal(await count(),0);
  checks.push('Exact-translation fixture preview stays read-only and cannot send while stopped.');
  await tab('chapter');await d.locator('[data-verse-form="chapter"] button').click();await page.waitForFunction(()=>window.previewShell.getObserver().session.control.verses.chapter?.rows.length===8);
  await d.locator('[data-verse="page"][data-page="1"]').click();await page.waitForFunction(()=>window.previewShell.getObserver().session.control.verses.chapter.page===1);
  await d.locator('[data-verse="select"]').first().click();await page.waitForFunction(()=>window.previewShell.getObserver().session.control.verses.selected.reference==='John 3:9');assert.equal(await count(),0);
  await page.screenshot({path:path.join(out,'verse-tools-chapter.png')});
  await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].setSize(660,620));assert.equal(await d.evaluate(e=>e.scrollWidth<=e.clientWidth+2),true);
  const scroll=await d.locator('.vv-verse-content').evaluate(e=>{e.scrollTop=e.scrollHeight;return e.scrollTop;});assert.ok(scroll>0);
  await page.screenshot({path:path.join(out,'verse-tools-narrow.png')});await page.keyboard.press('Escape');assert.equal(await page.evaluate(()=>document.activeElement?.dataset.verse),'open');await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].setSize(1180,880));
  checks.push('Chapter paging/selection sends nothing. Narrow popup scrolls without horizontal overflow; Escape restores launcher focus.');
  await page.locator('[data-consumer-prepare="start"]').click();await page.waitForFunction(()=>window.previewShell.getObserver().session.control.state==='running');
  await page.waitForFunction(()=>window.previewShell.getObserver().session.delivery_events.some(e=>e.reference==='John 3:17'&&e.outcome==='COMMAND_ACCEPTED'));
  await open();await page.waitForFunction(()=>window.previewShell.getObserver().session.control.pending.length>0);await d.locator('[data-engine-action="reject"]').first().click();await page.waitForFunction(()=>!window.previewShell.getObserver().session.control.pending.length);
  // Respect the configured 3-second cooldown after the synthetic STT command.
  await page.waitForTimeout(3500);
  await preview('John 3:21');await click('send');await page.waitForFunction(()=>window.previewShell.getObserver().session.control.verses.last_send?.outcome==='COMMAND_ACCEPTED');
  const sent=await page.evaluate(()=>window.previewShell.getObserver().session.control.verses.last_send),accepted=await count();
  await page.waitForFunction(()=>window.previewShell.getObserver().session.control.actions.includes('send_reference'));await click('send');await page.waitForFunction(id=>{const x=window.previewShell.getObserver().session.control.verses.last_send;return x.candidate_id!==id&&x.outcome==='SUPPRESSED';},sent.candidate_id);assert.equal(await count(),accepted);
  await tab('history');await d.locator('[data-verse="select"][data-reference="John 3:21"]').first().click();await page.waitForFunction(()=>window.previewShell.getObserver().session.control.verses.selected.status==='ready');assert.equal(await count(),accepted);
  checks.push('Packaged manual Send reaches real delivery logic and fake controller with one candidate ID; duplicate suppressed, history selection read-only, held decision reachable in popup.');
  await click('close');await page.locator('.vv-live-reference [data-verse-field="reference"]').fill('Luke 2:9');await page.evaluate(async()=>{const s=window.previewShell.getObserver().session;await window.verseviewDesktop.operator(s.session_id,'verse_preview',{reference:'John 3:22'});});await page.waitForFunction(()=>window.previewShell.getObserver().session.control.verses.selected.reference==='John 3:22'&&window.previewShell.getObserver().session.control.verses.selected.status==='ready');assert.equal(await page.locator('.vv-live-reference [data-verse-field="reference"]').inputValue(),'Luke 2:9');
  await page.locator('[data-operator="worship"]').click();await page.waitForFunction(()=>window.previewShell.getObserver().session.control.operator.worship);await open();await preview('John 3:22');await click('send');await page.waitForFunction(()=>{const x=window.previewShell.getObserver().session.control.verses.last_send;return x.reference==='John 3:22'&&x.outcome==='SUPPRESSED';});assert.equal(await count(),accepted);
  await context('John 4');await page.waitForFunction(()=>window.previewShell.getObserver().session.control.verses.context.chapter==='4');assert.equal(await count(),accepted);
  checks.push('Draft survives incoming updates; Worship suppresses manual Send; live context updates present nothing.');
  await d.locator('[data-live-stop]').click();await page.waitForFunction(()=>window.previewShell.getObserver().session.control.state==='stopped');assert.equal(await d.locator('[data-verse="send"]').isEnabled(),false);
  await context('John 5:2');await page.waitForFunction(()=>window.previewShell.getObserver().session.control.verses.context.staged&&window.previewShell.getObserver().session.control.verses.context.chapter==='5');assert.equal(await count(),accepted);checks.push('Stopped context stages for next Start without presenting.');
  assert.equal(await d.locator('[data-operator="emergency"]').isEnabled(),true);await d.locator('[data-operator="emergency"]').click();await page.waitForFunction(()=>window.previewShell.getObserver().session.control.operator.status==='saved'&&window.previewShell.getObserver().session.control.operator.emergency,{timeout:30000});checks.push('Stop invalidates selection; emergency saving remains accessible and confirms saved state.');
  await page.screenshot({path:path.join(out,'verse-tools-stopped.png')});assert.deepEqual(errors,[]);
  const processInfo=await app.evaluate(({app})=>({packaged:app.isPackaged,executable:process.execPath}));
  fs.writeFileSync(path.join(out,'verse-tools-ui-checks.json'),JSON.stringify({result:'PASS',checks,backend,processInfo,errors,manualCandidate:sent,microphoneSTT:'UNVERIFIED; synthetic callbacks',visibleVerseVIEW:'UNVERIFIED; fake controller and fixture text'},null,2)+'\n');console.log(JSON.stringify({result:'PASS',checks,processInfo},null,2));
  if(process.env.VV_VERSE_INSPECT==='1')await page.waitForTimeout(45000);
 }catch(e){if(page)await page.screenshot({path:path.join(out,'verse-tools-failure.png')}).catch(()=>{});throw e;}
 finally{if(app)await app.close();if(qaProfile&&path.basename(qaProfile)===tag&&path.basename(path.dirname(qaProfile))==='QA')fs.rmSync(qaProfile,{recursive:true,force:true});fs.rmSync(tmp,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1;});
