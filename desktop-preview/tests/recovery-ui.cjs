'use strict';
const { _electron } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict'), fs = require('node:fs'), os = require('node:os'), path = require('node:path');
const root = path.resolve(__dirname, '..'), output = path.join(root, 'test-results');
fs.mkdirSync(output, { recursive: true });
(async () => {
  if (!process.env.PREVIEW_EXECUTABLE) throw new Error('Use the packaged application with its native companion');
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'vv-recovery-ui-'));
  const source = path.join(directory, 'source'); fs.mkdirSync(source);
  const original = { language:'English', stt_engine:'deepgram', mic_index:0, dual_stt_enabled:true,
    secondary_language:'ml', secondary_stt_engine:'sarvam', bible_translation:'KJV',
    deepgram_api_key:'SECRET-STT-KEY', sarvam_api_key:'SECRET-SARVAM-KEY', confidence:.75,
    manual_confirm:true, verify:false, llm_enabled:false, auto_start:true, auto_save_notes:false,
    remote_url:'http://127.0.0.1:50010/control.html' };
  fs.writeFileSync(path.join(source,'settings.json'),JSON.stringify(original));
  const sourceBackend = fs.readFileSync(path.join(root,'backend-build/latest.txt'),'utf8').trim();
  const hiddenBackend = sourceBackend+'-hidden-for-recovery-verification';
  assert.ok(sourceBackend.startsWith(path.join(root,'backend-build')+path.sep));
  let application, page, app, backendProfile, childPid, layoutCases=0;
  const checks=[], errors=[];
  const action = name => app.locator(`[data-engine-action="${name}"]`);
  const alive = pid => {try {process.kill(pid,0);return true;}catch{return false;}};
  async function open(reset=false) {
    application = await _electron.launch({executablePath:process.env.PREVIEW_EXECUTABLE,args:[],
      env:{...process.env,VV_PREVIEW_TEST_PROFILE:'1',VV_BACKEND_VERIFY:'1',VV_BACKEND_SOURCE_PROFILE:source,
        VV_OBSERVER_TEST_DIRECTORY:path.join(directory,'empty-feed')}});
    backendProfile=path.join(await application.evaluate(({app})=>app.getPath('userData')),'Backend');
    assert.match(backendProfile,/[/\\]QA[/\\]Backend$/);
    if(reset)fs.rmSync(backendProfile,{recursive:true,force:true});
    page=await application.firstWindow();page.on('pageerror',error=>errors.push(error.message));
    await page.locator('#preview-mode').selectOption('observer');
    app=page.locator('#preview-surface');
    await app.getByRole('button',{name:'Live session',exact:true}).click();
    await app.locator('[data-backend-action="launch"]').click();
    await page.waitForFunction(()=>window.previewShell.getBackend().status==='ready');
    childPid=await page.evaluate(()=>window.previewShell.getBackend().pid);
    await page.waitForFunction(()=>window.previewShell.getObserver().session?.control?.state==='stopped');
  }
  try {
    fs.renameSync(sourceBackend,hiddenBackend);
    await open(true);
    const checkpoint=path.join(backendProfile,'Recovery/session.json');
    await action('start').click();
    await action('approve').waitFor();
    const pending=await page.evaluate(()=>window.previewShell.getObserver().session.control.pending[0]);
    const deadline=Date.now()+22000;
    while(!fs.existsSync(checkpoint)&&Date.now()<deadline)await page.waitForTimeout(200);
    assert.equal(fs.existsSync(checkpoint),true,'Periodic recovery checkpoint must exist before crashing');
    const saved=JSON.parse(fs.readFileSync(checkpoint,'utf8'));
    assert.equal(saved.reason,'autosave');
    assert.ok(saved.data.transcript.includes('John 3:17'));
    assert.ok(saved.data.transcript_secondary.includes('John 3:16'));
    assert.ok(saved.data.raw_preview.secondary.includes('യോഹന്നാൻ'));
    assert.equal(saved.data.verse_history.some(row=>row.ref==='John 3:18'),false);
    for(const excluded of ['settings','stt_log','discord_msg_id','pending','queue'])assert.equal(excluded in saved.data,false);
    assert.equal(JSON.stringify(saved).includes('SECRET-'),false);
    fs.writeFileSync(path.join(output,'recovery-autosave.json'),JSON.stringify({reason:saved.reason,saved_at:saved.saved_at,
      history:saved.data.verse_history,unapprovedCandidate:pending.candidate_id,unapprovedReference:pending.reference},null,2));
    process.kill(childPid,'SIGKILL');
    await page.waitForFunction(()=>window.previewShell.getBackend().status==='failed');
    await app.locator('[data-backend-action="launch"]').click();
    await page.waitForFunction(()=>window.previewShell.getBackend().status==='ready');
    childPid=await page.evaluate(()=>window.previewShell.getBackend().pid);
    await action('restore_session').waitFor();
    assert.equal(await action('start').isEnabled(),false);
    assert.equal(await page.evaluate(()=>window.previewShell.getObserver().session.delivery_events.length),0);
    assert.equal(await page.evaluate(()=>window.previewShell.getObserver().session.control.pending.length),0);
    checks.push('A real periodic checkpoint survives a deliberately killed frozen QA child, preserving both contexts/raw preview but excluding held decisions, commands, logs and credentials');
    await app.locator('[data-recovery-preview] summary').click();
    await page.waitForTimeout(1600);
    assert.equal(await app.locator('[data-recovery-preview]').getAttribute('open'),'');
    const old=await page.evaluate(()=>({session:window.previewShell.getObserver().session.session_id,
      revision:window.previewShell.getObserver().session.control.recovery.revision}));
    await page.evaluate(()=>{
      const node=document.querySelector('.vv-recovery-text');const range=document.createRange();range.selectNodeContents(node);
      const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);
    });
    saved.data.transcript+='\nRecovered marker from the last service.';
    fs.writeFileSync(checkpoint,JSON.stringify(saved));
    await page.waitForFunction(revision=>window.previewShell.getObserver().session.control.recovery.revision!==revision,old.revision);
    assert.equal(await action('restore_session').isEnabled(),false);
    await assert.rejects(page.evaluate(value=>window.verseviewDesktop.recoverSession(value.session,value.revision,true),old));
    await page.evaluate(()=>window.getSelection().removeAllRanges());
    await page.waitForFunction(()=>!document.querySelector('[data-engine-action="restore_session"]').disabled);
    for(const width of [1180,900,640]) {
      await application.evaluate(({BrowserWindow},size)=>BrowserWindow.getAllWindows()[0].setSize(size,650),width);
      for(const layout of ['studio','focus']) {
        await page.locator('#preview-layout').selectOption(layout);
        for(const theme of ['sage','midnight','glass','galaxy','aurora','ember']) {
          await app.locator('[data-setting="theme"]').selectOption(theme);
          await action('restore_session').scrollIntoViewIfNeeded();
          const bounds=await app.evaluate(surface=>({client:surface.clientWidth,scroll:surface.scrollWidth}));
          assert.ok(bounds.scroll<=bounds.client+1,JSON.stringify({width,layout,theme,bounds}));
          assert.equal(await action('restore_session').isEnabled(),true);layoutCases++;
        }
      }
    }
    await page.screenshot({path:path.join(output,'recovery-narrow.png')});
    await application.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].setSize(1180,845));
    await page.locator('#preview-layout').selectOption('studio');
    await action('restore_session').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control.recovery.status==='staged');
    assert.equal(await page.evaluate(()=>window.previewShell.getObserver().session.control.state),'stopped');
    assert.equal(await page.evaluate(()=>window.previewShell.getObserver().session.transcripts.length),0);
    assert.equal(await page.evaluate(()=>window.previewShell.getObserver().session.delivery_events.length),0);
    await page.screenshot({path:path.join(output,'recovery-prepared.png')});
    checks.push('Stale revisions are rejected while text selection is preserved; saved preview stays separate from live speech and accepted output; 36 theme/layout/size cases keep decisions accessible');
    await application.close();application=null;
    assert.equal(alive(childPid),false);
    await open();
    await action('restore_session').waitFor();
    checks.push('Closing after Restore but before Start retains the checkpoint and asks again on the next launch');
    await action('restore_session').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control.recovery.status==='staged');
    await action('start').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control?.state==='running');
    await action('stop').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control.state==='stopped');
    const resumed=JSON.parse(fs.readFileSync(checkpoint,'utf8'));
    assert.equal(resumed.reason,'stopped');
    assert.ok(resumed.data.transcript.includes('Recovered marker'));
    assert.ok(resumed.data.transcript_secondary.includes('John 3:16'));
    checks.push('Explicit Start configures then restores the saved buffers; a clean Stop persists the recovered marker before optional summary processing');
    await application.close();application=null;
    await open();
    await action('discard_session').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control.recovery.status==='none');
    assert.equal(fs.existsSync(checkpoint),false);
    assert.equal(await action('start').isEnabled(),true);
    fs.writeFileSync(checkpoint,'{SECRET-CORRUPT-CONTENT');
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control.recovery.status==='invalid');
    assert.equal(await action('restore_session').count(),0);
    assert.equal(await action('start').isEnabled(),false);
    assert.equal((await page.content()).includes('SECRET-CORRUPT-CONTENT'),false);
    await page.screenshot({path:path.join(output,'recovery-invalid.png')});
    await action('discard_session').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control.recovery.status==='none');
    assert.equal(fs.existsSync(checkpoint),false);
    checks.push('Explicit Discard removes only the private checkpoint; corrupt content is retained until a decision and never appears in the renderer');
    assert.deepEqual(JSON.parse(fs.readFileSync(path.join(source,'settings.json'))),original);
    const processInfo=await application.evaluate(({app})=>({executable:process.execPath,packaged:app.isPackaged,resources:process.resourcesPath}));
    const environment=await page.evaluate(()=>window.verseviewDesktop.environment());
    await application.close();application=null;
    assert.equal(alive(childPid),false);assert.deepEqual(errors,[]);
    const report={result:'PASS',testedAt:new Date().toISOString(),processInfo,environment,checks,layoutCases,errors,
      buildTreeHidden:true,engine:'actual frozen host/engine with mocked services and callback replay',
      microphoneSTT:'DEFERRED',visibleVerseVIEW:'DEFERRED',windowsGUI:'UNVERIFIED on this Mac'};
    fs.writeFileSync(path.join(output,'recovery-ui-checks.json'),JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify(report,null,2));
  } catch(error) {
    if(page)await page.screenshot({path:path.join(output,'recovery-failure.png')}).catch(()=>{});
    throw error;
  } finally {
    if(application)await application.close().catch(()=>{});
    if(childPid&&alive(childPid))process.kill(childPid,'SIGTERM');
    if(fs.existsSync(hiddenBackend))fs.renameSync(hiddenBackend,sourceBackend);
    fs.rmSync(directory,{recursive:true,force:true});
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
