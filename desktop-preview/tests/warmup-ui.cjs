'use strict';
const { _electron } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict'), fs = require('node:fs'), os = require('node:os'), path = require('node:path');
const root = path.resolve(__dirname, '..'), output = path.join(root, 'test-results');
fs.mkdirSync(output, {recursive:true});
(async()=>{
  if(!process.env.PREVIEW_EXECUTABLE)throw new Error('Use the packaged application with its native companion');
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'vv-warmup-ui-')),source=path.join(directory,'source');
  fs.mkdirSync(source);
  const original={language:'English',stt_engine:'deepgram',mic_index:0,deepgram_api_key:'SECRET-STT',
    manual_confirm:true,verify:false,llm_enabled:false,auto_save_notes:false,local_llm_enabled:true,
    local_llm_warm_at_start:true,local_llm_role_verse:'local',local_llm_role_summary:'local',
    local_llm_model:'SECRET-MODEL',local_llm_auth_token:'SECRET-LOCAL-TOKEN'};
  fs.writeFileSync(path.join(source,'settings.json'),JSON.stringify(original));
  const sourceBackend=fs.readFileSync(path.join(root,'backend-build/latest.txt'),'utf8').trim();
  assert.ok(sourceBackend.startsWith(path.join(root,'backend-build')+path.sep));
  const hiddenBackend=sourceBackend+'-hidden-for-warmup-verification';
  let application,page,profile,childPid,layoutCases=0;
  const checks=[],errors=[];
  const alive=pid=>{try{process.kill(pid,0);return true;}catch{return false;}};
  try{
    fs.renameSync(sourceBackend,hiddenBackend);
    application=await _electron.launch({executablePath:process.env.PREVIEW_EXECUTABLE,args:[],
      env:{...process.env,VV_PREVIEW_TEST_PROFILE:'1',VV_BACKEND_VERIFY:'1',VV_BACKEND_SOURCE_PROFILE:source,
        VV_OBSERVER_TEST_DIRECTORY:path.join(directory,'empty-feed')}});
    profile=path.join(await application.evaluate(({app})=>app.getPath('userData')),'Backend');
    assert.match(profile,/[/\\]QA[/\\]Backend$/);fs.rmSync(profile,{recursive:true,force:true});
    page=await application.firstWindow();page.on('pageerror',error=>errors.push(error.message));
    await page.locator('#preview-mode').selectOption('observer');
    const surface=page.locator('#preview-surface'),action=name=>surface.locator(`[data-engine-action="${name}"]`);
    await surface.getByRole('button',{name:'Live session',exact:true}).click();
    await surface.locator('[data-backend-action="launch"]').click();
    await page.waitForFunction(()=>window.previewShell.getBackend().status==='ready');
    childPid=await page.evaluate(()=>window.previewShell.getBackend().pid);
    await page.waitForFunction(()=>window.previewShell.getObserver().session?.control?.state==='stopped');
    assert.equal(await page.evaluate(()=>window.previewShell.getObserver().session.host.warmup.status),'off');
    await action('start').click();
    await page.waitForFunction(()=>{
      const s=window.previewShell.getObserver().session;
      return s?.host?.warmup?.status==='running'&&s.delivery_events.some(e=>e.outcome==='COMMAND_ACCEPTED');
    });
    await page.screenshot({path:path.join(output,'warmup-running.png')});
    await action('reject').waitFor();await action('reject').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session.host.warmup.status==='failed');
    const failure=await page.evaluate(()=>window.previewShell.getObserver().session);
    assert.equal(failure.control.state,'running');
    assert.ok(failure.delivery_events.some(e=>e.reference==='John 3:17'&&e.outcome==='COMMAND_ACCEPTED'));
    assert.deepEqual(failure.host.warmup.roles.map(r=>[r.role,r.status]),[['summary','failed'],['verse','warmed']]);
    assert.equal(JSON.stringify(failure).includes('SECRET-'),false);
    assert.equal((await page.content()).includes('SECRET-'),false);
    await page.screenshot({path:path.join(output,'warmup-failed.png')});
    checks.push('Actual frozen warmup overlaps synthetic reference acceptance and a manual decision; slow successful and failed completions stay separate from recognition/delivery and raw model/endpoint/exception details stay private');
    await action('stop').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control.state==='stopped');
    await action('start').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session.host.warmup.status==='running');
    await action('stop').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control.state==='stopped');
    assert.equal(await page.evaluate(()=>window.previewShell.getObserver().session.host.warmup.status),'cancelled');
    await action('start').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session.host.warmup.status==='busy');
    await page.waitForTimeout(4500);
    assert.equal(await page.evaluate(()=>window.previewShell.getObserver().session.host.warmup.status),'busy');
    assert.deepEqual(await page.evaluate(()=>window.previewShell.getObserver().session.host.warmup.roles),[]);
    await action('stop').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control.state==='stopped');
    checks.push('Stop cancels later roles and public results; immediate Start remains usable and skips overlapping warmup; completion from the stopped session cannot change the new session status');
    const settingsPath=path.join(profile,'settings.json'),values=JSON.parse(fs.readFileSync(settingsPath,'utf8'));
    fs.writeFileSync(settingsPath,JSON.stringify({...values,local_llm_role_summary:'cloud'}));
    await action('start').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session.host.warmup.status==='complete');
    assert.equal(await page.evaluate(()=>window.previewShell.getObserver().session.host.warmup.roles[0].role),'verse');
    for(const width of [1180,900,640]){
      await application.evaluate(({BrowserWindow},w)=>BrowserWindow.getAllWindows()[0].setSize(w,650),width);
      for(const layout of ['studio','focus']){
        await page.locator('#preview-layout').selectOption(layout);
        for(const theme of ['sage','midnight','glass','galaxy','aurora','ember']){
          await surface.locator('[data-setting="theme"]').selectOption(theme);
          await surface.locator('[data-warmup-status]').scrollIntoViewIfNeeded();
          assert.equal(await surface.locator('[data-warmup-status]').isVisible(),true);
          const bounds=await surface.evaluate(s=>({client:s.clientWidth,scroll:s.scrollWidth}));
          assert.ok(bounds.scroll<=bounds.client+1,JSON.stringify({width,layout,theme,bounds}));
          await action('stop').scrollIntoViewIfNeeded();assert.equal(await action('stop').isEnabled(),true);layoutCases++;
        }
      }
    }
    await page.screenshot({path:path.join(output,'warmup-narrow.png')});
    await action('stop').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control.state==='stopped');
    fs.writeFileSync(settingsPath,JSON.stringify({...values,local_llm_warm_at_start:false}));
    await action('start').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control.state==='running');
    assert.equal(await page.evaluate(()=>window.previewShell.getObserver().session.host.warmup.status),'off');
    checks.push('Later explicit Start uses newly configured roles; success and opt-out states work; 36 size/layout/theme cases retain readable status and usable Stop controls');
    const processInfo=await application.evaluate(({app})=>({executable:process.execPath,packaged:app.isPackaged,resources:process.resourcesPath}));
    const environment=await page.evaluate(()=>window.verseviewDesktop.environment());
    await application.close();application=null;
    assert.equal(alive(childPid),false);assert.deepEqual(errors,[]);
    assert.deepEqual(JSON.parse(fs.readFileSync(path.join(source,'settings.json'))),original);
    const report={result:'PASS',testedAt:new Date().toISOString(),processInfo,environment,checks,layoutCases,errors,
      buildTreeHidden:true,engine:'actual frozen host/engine; mocked local-model completions and speech services',
      microphoneSTT:'DEFERRED',realModels:'NOT USED',visibleVerseVIEW:'DEFERRED',windowsGUI:'UNVERIFIED on this Mac'};
    fs.writeFileSync(path.join(output,'warmup-ui-checks.json'),JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify(report,null,2));
  }catch(error){
    if(page)await page.screenshot({path:path.join(output,'warmup-failure.png')}).catch(()=>{});
    throw error;
  }finally{
    if(application)await application.close().catch(()=>{});
    if(childPid&&alive(childPid))process.kill(childPid,'SIGTERM');
    if(fs.existsSync(hiddenBackend))fs.renameSync(hiddenBackend,sourceBackend);
    if(profile)fs.rmSync(profile,{recursive:true,force:true});
    fs.rmSync(directory,{recursive:true,force:true});
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
