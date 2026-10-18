'use strict';
const {_electron}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const root=path.resolve(__dirname,'..'),output=path.join(root,'test-results');fs.mkdirSync(output,{recursive:true});
(async()=>{
  if(!process.env.PREVIEW_EXECUTABLE)throw new Error('Use the packaged application with its native companion');
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'vv-bot-ui-')),source=path.join(directory,'source');fs.mkdirSync(source);
  const original={language:'English',stt_engine:'deepgram',mic_index:0,deepgram_api_key:'SECRET-STT',manual_confirm:true,
    verify:false,llm_enabled:false,auto_save_notes:false,discord_bot_token:'SECRET-SYNTHETIC',qa_bot_silence:true,qa_bot_scenario:'start-and-goto'};
  fs.writeFileSync(path.join(source,'settings.json'),JSON.stringify(original));
  const sourceBackend=fs.readFileSync(path.join(root,'backend-build/latest.txt'),'utf8').trim(),hiddenBackend=sourceBackend+'-hidden-for-bot';
  assert.ok(sourceBackend.startsWith(path.join(root,'backend-build')+path.sep));
  let application,page,profile,childPid,botPid,layoutCases=0;const checks=[],errors=[];
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
    await nav('Settings');await surface.locator('[data-backend-action="launch"]').click();
    await page.waitForFunction(()=>window.previewShell.getBackend().status==='ready');
    childPid=await page.evaluate(()=>window.previewShell.getBackend().pid);
    await page.waitForFunction(()=>window.previewShell.getObserver().session?.control?.bot?.status==='stopped');
    assert.equal(await page.evaluate(()=>window.previewShell.getObserver().session.control.state),'stopped');
    // Explicit selection must follow the same owned backend after a bot Start.
    await page.evaluate(()=>window.verseviewDesktop.selectObserver(window.previewShell.getObserver().session.session_id));
    await action('start_bot').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session?.control?.bot?.status==='online');
    botPid=await page.evaluate(()=>window.previewShell.getObserver().session.control.bot.pid);assert.ok(alive(botPid));
    await page.waitForFunction(()=>window.previewShell.getObserver().session?.control?.bot?.events.some(e=>e.route==='/close'&&e.http_status===200));
    const session=await page.evaluate(()=>window.previewShell.getObserver().session);
    assert.equal(session.pid,childPid);assert.deepEqual(session.control.bot.proof,{frozen:true,guiImported:false});
    const accepted=session.delivery_events.filter(e=>e.outcome==='COMMAND_ACCEPTED');
    assert.deepEqual(accepted.map(e=>e.reference),['John 3:19','John 3:20']);
    assert.ok(accepted.every(e=>e.source==='DISCORD-MANUAL'&&e.stream==='unknown'));
    assert.equal(session.delivery_events.filter(e=>e.stage==='dedup'&&e.outcome==='SUPPRESSED').length,2);
    checks.push('Packaged app owns a frozen GUI-free synthetic bot child; explicit Start bot connects only the fake transport; authenticated HTTP Start rotates and follows the selected backend session; goto/next accepted, repeated prev/present retain duplicate suppression; no live Discord');
    for(const width of [1180,900,640]){
      await application.evaluate(({BrowserWindow},w)=>BrowserWindow.getAllWindows()[0].setSize(w,650),width);
      for(const layout of ['studio','focus']){
        await page.locator('#preview-layout').selectOption(layout);
        for(const theme of ['sage','midnight','glass','galaxy','aurora','ember']){
          await surface.locator('[data-setting="theme"]').selectOption(theme);
          await surface.locator('[data-bot-events]').evaluate(node=>{node.open=true;});
          await action('stop_bot').scrollIntoViewIfNeeded();assert.equal(await action('stop_bot').isEnabled(),true);
          const bounds=await surface.evaluate(s=>({client:s.clientWidth,scroll:s.scrollWidth}));
          assert.ok(bounds.scroll<=bounds.client+1,JSON.stringify({width,layout,theme,bounds}));layoutCases++;
        }
      }
    }
    await page.screenshot({path:path.join(output,'bot-narrow.png')});
    await action('stop_bot').click();await page.waitForFunction(()=>window.previewShell.getObserver().session.control.bot.status==='stopped');
    assert.equal(alive(botPid),false);assert.equal(await page.evaluate(()=>window.previewShell.getObserver().session.control.state),'running');
    await nav('Live session');await action('stop').click();await page.waitForFunction(()=>window.previewShell.getObserver().session.control.state==='stopped');
    await surface.locator('[data-backend-action="close"]').click();await page.waitForFunction(()=>window.previewShell.getBackend().status==='available');
    await surface.locator('[data-backend-action="launch"]').click();await page.waitForFunction(()=>window.previewShell.getBackend().status==='ready');
    childPid=await page.evaluate(()=>window.previewShell.getBackend().pid);
    await page.waitForFunction(()=>window.previewShell.getObserver().session?.control?.recovery?.status==='available');
    await nav('Settings');await action('start_bot').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control.bot.events.some(e=>e.route==='/start'&&e.http_status===409));
    assert.equal(await page.evaluate(()=>window.previewShell.getObserver().session.control.state),'stopped');
    botPid=await page.evaluate(()=>window.previewShell.getObserver().session.control.bot.pid);
    checks.push('36 size/layout/theme cases retain reachable Stop bot and scrollable recent commands; Stop bot leaves recognition running; a later remote Start cannot bypass a pending recovery decision');
    await application.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].setSize(1180,880));
    await page.locator('#preview-layout').selectOption('studio');await surface.locator('[data-bot-panel]').scrollIntoViewIfNeeded();
    await page.screenshot({path:path.join(output,'bot-controls.png')});
    const final=await page.evaluate(()=>window.previewShell.getObserver().session);
    assert.equal(JSON.stringify(final).includes('SECRET-'),false);assert.equal((await page.content()).includes('SECRET-'),false);
    const processInfo=await application.evaluate(({app})=>({executable:process.execPath,packaged:app.isPackaged,resources:process.resourcesPath}));
    const environment=await page.evaluate(()=>window.verseviewDesktop.environment());
    await application.close();application=null;assert.equal(alive(childPid),false);assert.equal(alive(botPid),false);assert.deepEqual(errors,[]);
    assert.deepEqual(JSON.parse(fs.readFileSync(path.join(source,'settings.json'))),original);
    const report={result:'PASS',testedAt:new Date().toISOString(),processInfo,environment,checks,layoutCases,errors,buildTreeHidden:true,
      botState:final.control.bot,accepted,discord:'SYNTHETIC CHILD — no Discord SDK/network or messages',microphoneSTT:'DEFERRED',
      visibleVerseVIEW:'DEFERRED — mocked controller',windowsGUI:'UNVERIFIED on this Mac',ownedChildrenStopped:true};
    fs.writeFileSync(path.join(output,'bot-ui-checks.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
  }catch(error){
    if(page){await page.screenshot({path:path.join(output,'bot-failure.png')}).catch(()=>{});
      fs.writeFileSync(path.join(output,'bot-failure-state.json'),JSON.stringify(await page.evaluate(()=>window.previewShell.getObserver()).catch(()=>null),null,2));}
    throw error;
  }finally{
    if(application)await application.close().catch(()=>{});
    if(childPid&&alive(childPid))process.kill(childPid,'SIGTERM');
    if(fs.existsSync(hiddenBackend))fs.renameSync(hiddenBackend,sourceBackend);
    if(profile)fs.rmSync(profile,{recursive:true,force:true});fs.rmSync(directory,{recursive:true,force:true});
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
