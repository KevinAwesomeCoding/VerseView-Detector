const enableDeveloper = require('./enable-developer.cjs');
'use strict';
const {_electron}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const root=path.resolve(__dirname,'..'),output=path.join(root,'test-results');fs.mkdirSync(output,{recursive:true});
(async()=>{
  if(!process.env.PREVIEW_EXECUTABLE)throw new Error('Use the packaged application with its native companion');
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'vv-suggestions-ui-')),source=path.join(directory,'source');fs.mkdirSync(source);
  const original={language:'English',stt_engine:'deepgram',mic_index:0,deepgram_api_key:'SECRET-STT',sarvam_api_key:'SECRET-SARVAM',
    dual_stt_enabled:true,secondary_language:'ml',secondary_stt_engine:'sarvam',manual_confirm:true,verify:false,llm_enabled:false,
    auto_save_notes:false,watcher_enabled:true,watcher_provider:'local',local_llm_enabled:true,local_llm_model:'SECRET-MODEL'};
  fs.writeFileSync(path.join(source,'settings.json'),JSON.stringify(original));
  const sourceBackend=fs.readFileSync(path.join(root,'backend-build/latest.txt'),'utf8').trim(),hiddenBackend=sourceBackend+'-hidden-for-suggestions';
  assert.ok(sourceBackend.startsWith(path.join(root,'backend-build')+path.sep));
  let application,page,profile,childPid,layoutCases=0;const checks=[],errors=[];
  const alive=pid=>{try{process.kill(pid,0);return true;}catch{return false;}};
  try{
    fs.renameSync(sourceBackend,hiddenBackend);
    application=await _electron.launch({executablePath:process.env.PREVIEW_EXECUTABLE,args:[],env:{...process.env,
      VV_PREVIEW_TEST_PROFILE:'1',VV_BACKEND_VERIFY:'1',VV_BACKEND_SOURCE_PROFILE:source,VV_OBSERVER_TEST_DIRECTORY:path.join(directory,'empty')}});
    profile=path.join(await application.evaluate(({app})=>app.getPath('userData')),'Backend');
    assert.match(profile,/[/\\]QA[/\\]Backend$/);fs.rmSync(profile,{recursive:true,force:true});
    page=await application.firstWindow(); await enableDeveloper(page);page.on('pageerror',e=>errors.push(e.message));
    await page.locator('#preview-mode').selectOption('observer');
    const surface=page.locator('#preview-surface'),action=name=>surface.locator(`[data-engine-action="${name}"]`);
    await surface.getByRole('button',{name:'Live session',exact:true}).click();
    await surface.locator('[data-backend-action="launch"]').click();
    await page.waitForFunction(()=>window.previewShell.getBackend().status==='ready');
    childPid=await page.evaluate(()=>window.previewShell.getBackend().pid);
    await page.waitForFunction(()=>window.previewShell.getObserver().session?.control?.state==='stopped');
    async function start(){
      await action('start').click();await action('reject').waitFor();await action('reject').click();
      await page.waitForFunction(()=>window.previewShell.getObserver().session.control?.suggestions?.rows.length===2);
    }
    await start();
    const initial=await page.evaluate(()=>window.previewShell.getObserver().session);
    assert.deepEqual(new Set(initial.control.suggestions.rows.map(row=>row.stream)),new Set(['primary','secondary']));
    assert.equal(initial.delivery_events.some(e=>['John 3:19','John 3:20'].includes(e.reference)&&e.outcome==='COMMAND_ACCEPTED'),false);
    await surface.locator('[data-suggestion-panel] summary').click();await page.waitForTimeout(1600);
    assert.equal(await surface.locator('[data-suggestion-panel]').getAttribute('open'),'');
    await page.screenshot({path:path.join(output,'suggestions-ready.png')});
    const old={session:initial.session_id,id:initial.control.suggestions.rows[0].id};
    await page.evaluate(()=>{
      const node=document.querySelector('.vv-suggestions-body strong'),range=document.createRange();range.selectNodeContents(node);
      const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);
    });
    await page.evaluate(session=>window.verseviewDesktop.stopEngine(session),old.session);
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control.state==='stopped');
    assert.equal(await surface.locator('[data-suggestion-id]').first().isEnabled(),false);
    await assert.rejects(page.evaluate(v=>window.verseviewDesktop.sendSuggestion(v.session,v.id),old));
    await page.evaluate(()=>window.getSelection().removeAllRanges());
    await start();
    const current=await page.evaluate(()=>window.previewShell.getObserver().session);
    assert.notEqual(current.session_id,old.session);
    assert.equal(await surface.locator('[data-suggestion-panel]').getAttribute('open'),null,'New sessions must not inherit an old expanded panel');
    await assert.rejects(page.evaluate(v=>window.verseviewDesktop.sendSuggestion(v.session,v.id),old));
    await assert.rejects(page.evaluate(v=>window.verseviewDesktop.sendSuggestion(v.session,v.id),{session:current.session_id,id:old.id}));
    await surface.locator('[data-suggestion-panel] summary').click();
    checks.push('Actual frozen bilingual watcher/model-reply processing produces separate passive suggestions without presenting them; expanded details persist; Stop and session rotation invalidate old actions even while suggestion text is selected');
    for(const stream of ['primary','secondary']){
      const row=current.control.suggestions.rows.find(r=>r.stream===stream);
      await surface.locator(`[data-suggestion-id="${row.id}"]`).click();
      await page.waitForFunction(identity=>window.previewShell.getObserver().session.control.suggestions.rows.some(r=>r.id===identity&&r.state==='accepted'),row.id);
      const state=await page.evaluate(()=>window.previewShell.getObserver().session),updated=state.control.suggestions.rows.find(r=>r.id===row.id);
      const events=state.delivery_events.filter(e=>e.candidate_id===updated.candidate_id);
      assert.ok(events.some(e=>e.outcome==='COMMAND_ACCEPTED'&&e.source==='WATCHER-MANUAL'&&e.stream===stream));
      assert.equal(await surface.locator(`[data-suggestion-id="${row.id}"]`).isEnabled(),false);
      assert.equal(await surface.locator('.vv-output-ref').textContent(),row.reference);
      await assert.rejects(page.evaluate(v=>window.verseviewDesktop.sendSuggestion(v.session,v.id),{session:state.session_id,id:row.id}));
    }
    checks.push('Explicit operator sends use the actual engine/controller delivery boundary, retain primary/secondary attribution and correlate acceptance to candidate IDs; accepted suggestions cannot be blindly sent again');
    for(const width of [1180,900,640]){
      await application.evaluate(({BrowserWindow},w)=>BrowserWindow.getAllWindows()[0].setSize(w,650),width);
      for(const layout of ['studio','focus']){
        await page.locator('#preview-layout').selectOption(layout);
        for(const theme of ['sage','midnight','glass','galaxy','aurora','ember']){
          await surface.locator('[data-setting="theme"]').selectOption(theme);
          await surface.locator('[data-suggestion-panel]').scrollIntoViewIfNeeded();
          await surface.locator('[data-suggestion-id]').last().scrollIntoViewIfNeeded();
          const bounds=await surface.evaluate(s=>({client:s.clientWidth,scroll:s.scrollWidth}));
          assert.ok(bounds.scroll<=bounds.client+1,JSON.stringify({width,layout,theme,bounds}));
          assert.equal(await surface.locator('[data-suggestion-id]').last().isVisible(),true);
          await action('stop').scrollIntoViewIfNeeded();assert.equal(await action('stop').isEnabled(),true);layoutCases++;
        }
      }
    }
    await surface.locator('[data-suggestion-panel]').scrollIntoViewIfNeeded();
    await page.screenshot({path:path.join(output,'suggestions-narrow.png')});
    const final=await page.evaluate(()=>window.previewShell.getObserver().session);
    assert.equal(JSON.stringify(final).includes('SECRET-'),false);assert.equal((await page.content()).includes('SECRET-'),false);
    const processInfo=await application.evaluate(({app})=>({executable:process.execPath,packaged:app.isPackaged,resources:process.resourcesPath}));
    const environment=await page.evaluate(()=>window.verseviewDesktop.environment());
    await application.close();application=null;assert.equal(alive(childPid),false);assert.deepEqual(errors,[]);
    assert.deepEqual(JSON.parse(fs.readFileSync(path.join(source,'settings.json'))),original);
    const report={result:'PASS',testedAt:new Date().toISOString(),processInfo,environment,checks,layoutCases,errors,buildTreeHidden:true,
      acceptedEvents:final.delivery_events.filter(e=>e.source==='WATCHER-MANUAL'),
      engine:'actual frozen bilingual watcher and manual-delivery path with mocked speech/model/browser services',
      expiry:'90-second TTL checked in focused unit tests',microphoneSTT:'DEFERRED',realModels:'NOT USED',visibleVerseVIEW:'DEFERRED',windowsGUI:'UNVERIFIED on this Mac'};
    fs.writeFileSync(path.join(output,'suggestions-ui-checks.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
  }catch(error){
    if(page){
      await page.screenshot({path:path.join(output,'suggestions-failure.png')}).catch(()=>{});
      const snapshot=await page.evaluate(()=>window.previewShell.getObserver()).catch(()=>null);
      fs.writeFileSync(path.join(output,'suggestions-failure-state.json'),JSON.stringify(snapshot,null,2));
    }
    throw error;
  }
  finally{
    if(application)await application.close().catch(()=>{});
    if(childPid&&alive(childPid))process.kill(childPid,'SIGTERM');
    if(fs.existsSync(hiddenBackend))fs.renameSync(hiddenBackend,sourceBackend);
    if(profile)fs.rmSync(profile,{recursive:true,force:true});fs.rmSync(directory,{recursive:true,force:true});
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
