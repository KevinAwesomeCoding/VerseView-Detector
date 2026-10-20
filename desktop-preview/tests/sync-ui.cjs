const enableDeveloper = require('./enable-developer.cjs');
'use strict';
const {_electron}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const root=path.resolve(__dirname,'..'),output=path.join(root,'test-results');fs.mkdirSync(output,{recursive:true});
(async()=>{
  if(!process.env.PREVIEW_EXECUTABLE)throw new Error('Use the packaged application with its native companion');
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'vv-sync-ui-')),source=path.join(directory,'source');fs.mkdirSync(source);
  const original={language:'English',stt_engine:'deepgram',mic_index:0,deepgram_api_key:'SECRET-OLD-STT',discord_bot_token:'SECRET-OLD-BOT',
    settings_sync_url:'https://sync.invalid/SECRET/slow',dedup_window:91,future:{keep:42},manual_confirm:true,verify:false,llm_enabled:false,auto_save_notes:false};
  fs.writeFileSync(path.join(source,'settings.json'),JSON.stringify(original));
  const sourceBackend=fs.readFileSync(path.join(root,'backend-build/latest.txt'),'utf8').trim(),hiddenBackend=sourceBackend+'-hidden-for-sync';
  assert.ok(sourceBackend.startsWith(path.join(root,'backend-build')+path.sep));
  let application,page,profile,childPid,layoutCases=0;const checks=[],errors=[];
  const alive=pid=>{try{process.kill(pid,0);return true;}catch{return false;}};
  try{
    fs.renameSync(sourceBackend,hiddenBackend);
    application=await _electron.launch({executablePath:process.env.PREVIEW_EXECUTABLE,args:[],env:{...process.env,
      VV_PREVIEW_TEST_PROFILE:'1',VV_BACKEND_VERIFY:'1',VV_BACKEND_SOURCE_PROFILE:source,VV_OBSERVER_TEST_DIRECTORY:path.join(directory,'empty')}});
    profile=path.join(await application.evaluate(({app})=>app.getPath('userData')),'Backend');
    assert.match(profile,/[/\\]QA[/\\]Backend$/);fs.rmSync(profile,{recursive:true,force:true});
    const settingsPath=path.join(profile,'settings.json');
    const changeURL=suffix=>{const values=JSON.parse(fs.readFileSync(settingsPath));values.settings_sync_url='https://sync.invalid/SECRET/'+suffix;fs.writeFileSync(settingsPath,JSON.stringify(values));};
    page=await application.firstWindow(); await enableDeveloper(page);page.on('pageerror',e=>errors.push(e.message));
    await page.locator('#preview-mode').selectOption('observer');const surface=page.locator('#preview-surface');
    const action=name=>surface.locator(`[data-engine-action="${name}"]`);
    await surface.getByRole('button',{name:'Settings',exact:true}).filter({visible:true}).click();
    await surface.locator('[data-backend-action="launch"]').click();await page.waitForFunction(()=>window.previewShell.getBackend().status==='ready');
    childPid=await page.evaluate(()=>window.previewShell.getBackend().pid);
    await page.waitForFunction(()=>window.previewShell.getObserver().session?.control?.sync?.status==='pulling');
    assert.equal(await action('pull_settings').isDisabled(),true);assert.equal(await action('start_bot').isDisabled(),true);
    assert.equal(await surface.locator('[data-detector-setting="bible_translation"]').isDisabled(),true);
    await assert.rejects(page.evaluate(()=>window.verseviewDesktop.startEngine(window.previewShell.getObserver().session.session_id)));
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control.sync.status==='applied');
    const saved=JSON.parse(fs.readFileSync(settingsPath));assert.equal(saved.deepgram_api_key,'SECRET-SYNCED-STT');assert.equal(saved.discord_bot_token,'SECRET-SYNCED-BOT');
    assert.deepEqual(saved.future,{keep:42});assert.equal(saved.dedup_window,91);assert.equal(saved.language,'English');assert.ok(fs.existsSync(saved.gcp_credentials_path));
    assert.equal(await page.evaluate(()=>window.previewShell.getObserver().session.control.state),'stopped');
    assert.equal(await page.evaluate(()=>window.previewShell.getObserver().session.control.sync.updated_count),3);
    checks.push('Actual packaged/frozen backend performs the saved opt-in startup pull through a fake downloader, updates only whitelisted credentials and a private portable GCP file, blocks recognition/bot/settings actions during pull, and leaves recognition stopped');
    await surface.locator('[data-detector-setting="bible_translation"]').selectOption('WEB');
    const before=fs.readFileSync(settingsPath,'utf8');await action('pull_settings').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control.sync.status==='unchanged');
    assert.equal(fs.readFileSync(settingsPath,'utf8'),before);assert.equal(await surface.locator('[data-detector-setting="bible_translation"]').inputValue(),'WEB');
    changeURL('failure');const failedBefore=fs.readFileSync(settingsPath,'utf8');await action('pull_settings').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control.sync.status==='failed');assert.equal(fs.readFileSync(settingsPath,'utf8'),failedBefore);
    changeURL('slow');await action('pull_settings').click();await page.waitForFunction(()=>window.previewShell.getObserver().session.control.sync.status==='pulling');
    const edited=JSON.parse(fs.readFileSync(settingsPath));edited.future='Operator correction';fs.writeFileSync(settingsPath,JSON.stringify(edited));
    const editedBefore=fs.readFileSync(settingsPath,'utf8');await page.waitForFunction(()=>window.previewShell.getObserver().session.control.sync.status==='conflict');
    assert.equal(fs.readFileSync(settingsPath,'utf8'),editedBefore);assert.equal(await surface.locator('[data-detector-setting="bible_translation"]').inputValue(),'WEB');
    assert.match(await surface.locator('[data-settings-status]').textContent(),/changed elsewhere/i);
    await surface.locator('[data-reload-settings]').click();assert.equal(await surface.locator('[data-detector-setting="bible_translation"]').inputValue(),'KJV');
    checks.push('Unchanged pulls skip settings writes; fake failure and in-flight operator edit preserve the private file; a dirty non-secret form keeps its draft and requires Reload rather than silently overwriting it');
    for(const width of [1180,900,640]){
      await application.evaluate(({BrowserWindow},w)=>BrowserWindow.getAllWindows()[0].setSize(w,650),width);
      for(const layout of ['studio','focus']){
        await page.locator('#preview-layout').selectOption(layout);
        for(const theme of ['sage','midnight','glass','galaxy','aurora','ember']){
          await surface.locator('[data-setting="theme"]').selectOption(theme);await action('pull_settings').scrollIntoViewIfNeeded();
          assert.equal(await action('pull_settings').isEnabled(),true);
          const bounds=await surface.evaluate(s=>({client:s.clientWidth,scroll:s.scrollWidth}));assert.ok(bounds.scroll<=bounds.client+1,JSON.stringify({width,layout,theme,bounds}));
          await surface.locator('[data-backend-action="close"]').scrollIntoViewIfNeeded();assert.equal(await surface.locator('[data-backend-action="close"]').isEnabled(),true);layoutCases++;
        }
      }
    }
    await surface.locator('[data-sync-panel]').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(output,'sync-narrow.png')});
    await application.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].setSize(1180,880));await page.locator('#preview-layout').selectOption('studio');
    await surface.locator('[data-sync-panel]').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(output,'sync-status.png')});
    const final=await page.evaluate(()=>window.previewShell.getObserver().session);assert.equal(JSON.stringify(final).includes('SECRET'),false);assert.equal((await page.content()).includes('SECRET'),false);
    const processInfo=await application.evaluate(({app})=>({executable:process.execPath,packaged:app.isPackaged,resources:process.resourcesPath}));
    const environment=await page.evaluate(()=>window.verseviewDesktop.environment());
    await action('pull_settings').click();await page.waitForFunction(()=>window.previewShell.getObserver().session.control.sync.status==='pulling');
    const closeBefore=fs.readFileSync(settingsPath,'utf8');await application.close();application=null;
    assert.equal(alive(childPid),false);assert.equal(fs.readFileSync(settingsPath,'utf8'),closeBefore);assert.deepEqual(errors,[]);
    assert.deepEqual(JSON.parse(fs.readFileSync(path.join(source,'settings.json'))),original);
    checks.push('36 width/layout/theme cases retain readable status and accessible Pull/Close controls; quitting during a delayed fake pull discards its result and exits the owned backend; original source profile unchanged');
    const report={result:'PASS',testedAt:new Date().toISOString(),processInfo,environment,checks,layoutCases,errors,buildTreeHidden:true,
      syncState:final.control.sync,ownedChildrenStopped:true,download:'SYNTHETIC — no real sync URL or credentials contacted',
      microphoneSTT:'NOT USED',visibleVerseVIEW:'NOT USED',windowsGUI:'UNVERIFIED on this Mac'};
    fs.writeFileSync(path.join(output,'sync-ui-checks.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
  }catch(error){
    if(page){await page.screenshot({path:path.join(output,'sync-failure.png')}).catch(()=>{});
      fs.writeFileSync(path.join(output,'sync-failure-state.json'),JSON.stringify(await page.evaluate(()=>window.previewShell.getObserver()).catch(()=>null),null,2));}
    throw error;
  }finally{
    if(application)await application.close().catch(()=>{});if(childPid&&alive(childPid))process.kill(childPid,'SIGTERM');
    if(fs.existsSync(hiddenBackend))fs.renameSync(hiddenBackend,sourceBackend);if(profile)fs.rmSync(profile,{recursive:true,force:true});fs.rmSync(directory,{recursive:true,force:true});
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
