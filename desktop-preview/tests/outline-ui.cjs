'use strict';
const {_electron}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const root=path.resolve(__dirname,'..'),output=path.join(root,'test-results');fs.mkdirSync(output,{recursive:true});
(async()=>{
  if(!process.env.PREVIEW_EXECUTABLE)throw new Error('Use the packaged application with its native companion');
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'vv-outline-ui-')),source=path.join(directory,'source');fs.mkdirSync(source);
  const original={language:'English',stt_engine:'deepgram',mic_index:0,deepgram_api_key:'SECRET-STT',sarvam_api_key:'SECRET-SARVAM',
    dual_stt_enabled:true,secondary_language:'ml',secondary_stt_engine:'sarvam',manual_confirm:true,verify:false,llm_enabled:true,
    auto_save_notes:false,live_points_llm_enabled:true,live_points_prompt:'Capture only the synthetic speech.',
    local_llm_enabled:true,local_llm_role_outline:'local',local_llm_model:'SECRET-MODEL'};
  fs.writeFileSync(path.join(source,'settings.json'),JSON.stringify(original));
  const sourceBackend=fs.readFileSync(path.join(root,'backend-build/latest.txt'),'utf8').trim(),hiddenBackend=sourceBackend+'-hidden-for-outline';
  assert.ok(sourceBackend.startsWith(path.join(root,'backend-build')+path.sep));
  let application,page,profile,childPid,layoutCases=0;const checks=[],errors=[];
  const alive=pid=>{try{process.kill(pid,0);return true;}catch{return false;}};
  try{
    fs.renameSync(sourceBackend,hiddenBackend);
    application=await _electron.launch({executablePath:process.env.PREVIEW_EXECUTABLE,args:[],env:{...process.env,
      VV_PREVIEW_TEST_PROFILE:'1',VV_BACKEND_VERIFY:'1',VV_BACKEND_SOURCE_PROFILE:source,VV_OBSERVER_TEST_DIRECTORY:path.join(directory,'empty')}});
    profile=path.join(await application.evaluate(({app})=>app.getPath('userData')),'Backend');
    assert.match(profile,/[/\\]QA[/\\]Backend$/);fs.rmSync(profile,{recursive:true,force:true});
    page=await application.firstWindow();page.on('pageerror',e=>errors.push(e.message));
    await page.locator('#preview-mode').selectOption('observer');
    const surface=page.locator('#preview-surface'),action=name=>surface.locator(`[data-engine-action="${name}"]`);
    const nav=label=>surface.getByRole('button',{name:label,exact:true}).filter({visible:true}).click();
    await nav('Outline');await surface.locator('[data-backend-action="launch"]').click();
    await page.waitForFunction(()=>window.previewShell.getBackend().status==='ready');
    childPid=await page.evaluate(()=>window.previewShell.getBackend().pid);
    await page.waitForFunction(()=>window.previewShell.getObserver().session?.control?.state==='stopped');
    assert.equal(await page.evaluate(()=>window.verseviewDesktop.outlineOutputState()).then(v=>v.open),false);
    assert.equal(await application.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows().length),1);
    await surface.locator('[data-outline-text]').fill('Pre-start operator notes.');
    await surface.locator('[data-outline-save]').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control.outline.text==='Pre-start operator notes.');
    assert.equal(await page.evaluate(()=>window.previewShell.getObserver().session.control.state),'stopped');
    await action('start').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control?.outline?.source==='model');
    assert.match(await surface.locator('[data-outline-text]').inputValue(),/SYNTHETIC SERMON OUTLINE/);
    await action('reject').waitFor();await action('reject').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control.outline.status==='generating');
    const before=await page.evaluate(()=>({session:window.previewShell.getObserver().session.session_id,
      revision:window.previewShell.getObserver().session.control.outline.revision}));
    const manual='[OPERATOR-MARKER] മലയാളം കുറിപ്പുകൾ. <script>literal notes</script>';
    await surface.locator('[data-outline-text]').fill(manual);await surface.locator('[data-outline-save]').click();
    await page.waitForFunction(text=>window.previewShell.getObserver().session.control.outline.text===text,manual);
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control.outline.message.includes('skipped'));
    assert.equal(await surface.locator('[data-outline-text]').inputValue(),manual);
    assert.match(await surface.locator('[data-outline-status]').textContent(),/skipped/);
    await assert.rejects(page.evaluate(v=>window.verseviewDesktop.editOutline(v.session,v.revision,'Stale overwrite'),before));
    assert.equal(await page.evaluate(()=>window.verseviewDesktop.outlineOutputState()).then(v=>v.open),false);
    assert.equal(await application.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows().length),1);
    const events=await page.evaluate(()=>window.previewShell.getObserver().session.delivery_events);
    assert.ok(events.some(e=>e.reference==='John 3:17'&&e.outcome==='COMMAND_ACCEPTED'));
    checks.push('Actual frozen outline loop receives mocked completions while synthetic bilingual transcription/delivery continue; stopped manual edits work; saving during an in-flight generation preserves newer notes and reports the skipped stale reply; stale IPC edits reject');
    for(const width of [1180,900,640]){
      await application.evaluate(({BrowserWindow},w)=>BrowserWindow.getAllWindows()[0].setSize(w,650),width);
      for(const layout of ['studio','focus']){
        await page.locator('#preview-layout').selectOption(layout);
        for(const theme of ['sage','midnight','glass','galaxy','aurora','ember']){
          await surface.locator('[data-setting="theme"]').selectOption(theme);
          assert.equal(await surface.locator('[data-outline-text]').inputValue(),manual);
          await surface.locator('[data-outline-reload]').scrollIntoViewIfNeeded();
          assert.equal(await surface.locator('[data-outline-reload]').isVisible(),true);
          const bounds=await surface.evaluate(s=>({client:s.clientWidth,scroll:s.scrollWidth}));
          assert.ok(bounds.scroll<=bounds.client+1,JSON.stringify({width,layout,theme,bounds}));
          await action('stop').scrollIntoViewIfNeeded();assert.equal(await action('stop').isEnabled(),true);layoutCases++;
        }
      }
    }
    await surface.locator('[data-outline-text]').scrollIntoViewIfNeeded();
    await page.screenshot({path:path.join(output,'outline-narrow.png')});
    await action('stop').click();await page.waitForFunction(()=>window.previewShell.getObserver().session.control.state==='stopped');
    await action('start').click();await page.waitForFunction(()=>window.previewShell.getObserver().session.control.outline.status==='generating');
    await action('stop').click();await page.waitForFunction(()=>window.previewShell.getObserver().session.control.state==='stopping');
    assert.equal(await surface.locator('[data-outline-text]').isEnabled(),false);
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control.state==='stopped');
    assert.equal(await page.evaluate(()=>window.previewShell.getObserver().session.control.outline.text),manual);
    checks.push('36 size/layout/theme cases preserve notes and reachable controls; Stop remains Stopping while the mocked provider call drains, then no stale result changes the notes; output windows never open automatically');
    await application.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].setSize(1180,880));
    await page.locator('#preview-layout').selectOption('studio');await surface.locator('[data-outline-text]').scrollIntoViewIfNeeded();
    await page.screenshot({path:path.join(output,'outline-notes.png')});
    const final=await page.evaluate(()=>window.previewShell.getObserver().session);
    assert.equal(JSON.stringify(final).includes('SECRET-'),false);assert.equal((await page.content()).includes('SECRET-'),false);
    const processInfo=await application.evaluate(({app})=>({executable:process.execPath,packaged:app.isPackaged,resources:process.resourcesPath}));
    const environment=await page.evaluate(()=>window.verseviewDesktop.environment());
    await application.close();application=null;assert.equal(alive(childPid),false);assert.deepEqual(errors,[]);
    assert.deepEqual(JSON.parse(fs.readFileSync(path.join(source,'settings.json'))),original);
    const report={result:'PASS',testedAt:new Date().toISOString(),processInfo,environment,checks,layoutCases,errors,buildTreeHidden:true,
      outlineState:final.control.outline,engine:'actual frozen outline loop with mocked model/STT/browser services; QA accelerates only outline intervals',
      outputWindow:'NOT OPENED - physical checks deferred; routing/window lifecycle covered with injected-window unit tests',
      microphoneSTT:'DEFERRED',realModels:'NOT USED',visibleVerseVIEW:'DEFERRED',windowsGUI:'UNVERIFIED on this Mac'};
    fs.writeFileSync(path.join(output,'outline-ui-checks.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
  }catch(error){
    if(page){await page.screenshot({path:path.join(output,'outline-failure.png')}).catch(()=>{});
      fs.writeFileSync(path.join(output,'outline-failure-state.json'),JSON.stringify(await page.evaluate(()=>window.previewShell.getObserver()).catch(()=>null),null,2));}
    throw error;
  }finally{
    if(application)await application.close().catch(()=>{});
    if(childPid&&alive(childPid))process.kill(childPid,'SIGTERM');
    if(fs.existsSync(hiddenBackend))fs.renameSync(hiddenBackend,sourceBackend);
    if(profile)fs.rmSync(profile,{recursive:true,force:true});fs.rmSync(directory,{recursive:true,force:true});
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
