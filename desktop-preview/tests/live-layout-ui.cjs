'use strict';
// Consumer layout acceptance with the frozen QA backend; no real mic/provider/display.
const {_electron}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const root=path.resolve(__dirname,'..'),out=path.join(root,'test-results','live-layout');
fs.mkdirSync(out,{recursive:true});
(async()=>{
  const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'vv-live-layout-')),source=path.join(temporary,'source'),tag=`live-layout-${process.pid}`;
  fs.mkdirSync(source);
  fs.writeFileSync(path.join(source,'settings.json'),JSON.stringify({language:'English',stt_engine:'deepgram',
    deepgram_api_key:'SYNTHETIC-ONLY',sarvam_api_key:'SYNTHETIC-ONLY',dual_stt_enabled:true,
    secondary_language:'ml',secondary_stt_engine:'sarvam',mic_index:0,bible_translation:'KJV',
    remote_url:'http://127.0.0.1:50010/control.html',settings_sync_url:'',manual_confirm:true,
    verify:false,auto_start:false,auto_save_notes:false,llm_enabled:false}));
  let app,page,profile;const checks=[],errors=[];
  const visible=selector=>page.locator(selector).filter({visible:true});
  const accepted=()=>page.evaluate(()=>window.previewShell.getObserver().session.delivery_events.filter(e=>e.outcome==='COMMAND_ACCEPTED').length);
  async function launch(){
    app=await _electron.launch({executablePath:process.env.PREVIEW_EXECUTABLE||require('electron'),args:process.env.PREVIEW_EXECUTABLE?[]:[root],env:{...process.env,
      VV_PREVIEW_TEST_PROFILE:'1',VV_PREVIEW_TEST_PROFILE_TAG:tag,VV_BACKEND_VERIFY:'1',VV_BACKEND_SOURCE_PROFILE:source,
      VV_OBSERVER_TEST_DIRECTORY:path.join(temporary,'empty')}});
    page=await app.firstWindow();page.on('pageerror',e=>errors.push(e.message));
    profile=await app.evaluate(({app})=>app.getPath('userData'));
    assert.equal(path.basename(profile),tag);assert.equal(path.basename(path.dirname(profile)),'QA');
    await page.locator('[data-consumer-prepare="settings"]').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session?.control?.verses,{timeout:30000});
    assert.equal(await page.evaluate(()=>window.previewShell.isDeveloper()),false);
    const backend=await page.evaluate(()=>window.previewShell.getBackend());
    assert.equal(backend.frozen,true);assert.equal(backend.verification,true);assert.equal(backend.guiImported,false);
    return backend;
  }
  try{
    const backend=await launch();
    const header=page.locator('.vv-live-controls'),manual=page.locator('.vv-live-reference'),dialog=page.locator('.vv-verse-dialog');
    for(const action of ['emergency','worship','pin','save'])assert.equal(await header.locator(`[data-operator="${action}"]`).count(),1);
    assert.equal(await page.locator('.vv-content [data-operator="save"]').count(),0);
    assert.equal(await visible('[data-operator="open"]').count(),1);
    assert.equal(await visible('[data-operator="open"]').evaluate(e=>Boolean(e.closest('[aria-label="Dashboard navigation"]'))),true);
    assert.equal(await manual.evaluate(e=>Boolean(e.previousElementSibling?.matches('.vv-stream-section'))),true);
    const input=manual.locator('[data-verse-field="reference"]');
    await input.fill('John 3:21');await manual.getByRole('button',{name:'Preview reference',exact:true}).click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control.verses.selected?.status==='ready');
    assert.match(await manual.locator('.vv-verse-text').innerText(),/QA fixture KJV/);
    assert.equal(await manual.locator('[data-verse="send"]').isEnabled(),false);assert.equal(await accepted(),0);
    checks.push('Header controls are together, Saved sessions is in workspace navigation, reference entry follows both transcripts, and preview stays read-only');
    await input.fill('Luke 2:9');await input.focus();await input.evaluate(e=>e.setSelectionRange(4,4));
    await page.evaluate(async()=>{const s=window.previewShell.getObserver().session;await window.verseviewDesktop.operator(s.session_id,'verse_preview',{reference:'John 3:22'});});
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control.verses.selected?.reference==='John 3:22'&&window.previewShell.getObserver().session.control.verses.selected?.status==='ready');
    assert.equal(await input.inputValue(),'Luke 2:9');assert.equal(await input.evaluate(e=>document.activeElement===e&&e.selectionStart===4),true);
    await page.evaluate(()=>document.getElementById('verseview-prototype').dispatchEvent(new Event('preview:environment')));
    assert.equal(await input.evaluate(e=>document.activeElement===e&&e.selectionStart===4),true);
    await manual.locator('[data-live-reference-preview] summary').click();
    await page.evaluate(async()=>{const s=window.previewShell.getObserver().session;await window.verseviewDesktop.operator(s.session_id,'list_sessions',{page:0});});
    await page.waitForTimeout(900);assert.equal(await manual.locator('[data-live-reference-preview]').evaluate(e=>e.open),false);
    await manual.locator('[data-verse="open"]').click();
    assert.equal(await dialog.locator('[data-tab="reference"]').count(),0);
    assert.equal(await dialog.locator('[data-tab="context"]').getAttribute('aria-selected'),'true');
    await dialog.locator('[data-verse-field="context"]').fill('John 4');
    await dialog.locator('[data-verse-form="context"] button[type="submit"]').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control.verses.context.chapter==='4');
    await page.keyboard.press('Escape');assert.equal(await input.inputValue(),'Luke 2:9');
    await manual.locator('[data-verse="open-chapter"]').click();
    assert.equal(await dialog.locator('[data-tab="chapter"]').getAttribute('aria-selected'),'true');
    assert.equal(await dialog.locator('[data-verse-field="book"]').inputValue(),'John');
    assert.equal(await dialog.locator('[data-verse-field="chapter"]').inputValue(),'4');
    await dialog.locator('[data-verse-form="chapter"] button').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control.verses.chapter?.reference==='John 4'&&window.previewShell.getObserver().session.control.verses.chapter?.status==='ready');
    assert.equal(await accepted(),0);await page.keyboard.press('Escape');
    checks.push('Manual draft, caret and collapsed preview survive feed updates; Context/Chapter/History remain in tools; quick chapter uses acknowledged context without presentation');
    await header.locator('[data-operator="pin"]').click();assert.equal(await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].isAlwaysOnTop()),true);
    await header.locator('[data-operator="pin"]').click();
    await header.locator('[data-operator="worship"]').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control.operator.worship);
    await header.locator('[data-consumer-prepare="start"]').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control.state==='running',{timeout:30000});
    await page.waitForFunction(()=>window.previewShell.getObserver().session.transcripts.some(r=>r.stream==='secondary'));
    await header.locator('[data-operator="save"]').click();
    await page.waitForFunction(()=>{const op=window.previewShell.getObserver().session.control.operator;return op.saved?.id&&op.status==='saved'&&!op.busy;});
    await header.locator('[data-operator="save"]').waitFor({state:'visible'});
    assert.match(await visible('[data-operator="open"]').innerText(),/Saved/);
    await visible('[data-operator="open"]').click();
    await page.locator('.vv-session-dialog[open] .vv-session-row').first().click();
    await page.waitForFunction(()=>Boolean(window.previewShell.getObserver().session.control.operator.library.selected));
    assert.equal(await accepted(),0);
    await app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows()[0].setSize(660,620));
    await page.keyboard.press('Escape');
    await page.waitForFunction(()=>[...document.querySelectorAll('[data-operator="open"]')].some(e=>e.getClientRects().length&&document.activeElement===e));
    assert.equal(await visible('[data-operator="open"]').evaluate(e=>document.activeElement===e),true);
    await page.evaluate(()=>document.getElementById('verseview-prototype').dispatchEvent(new Event('preview:environment')));
    assert.equal(await visible('[data-operator="open"]').evaluate(e=>document.activeElement===e),true);
    await visible('[data-operator="open"]').click();await page.keyboard.press('Escape');
    checks.push('Native pinning, Worship, saving, bilingual session browsing and popup focus return work from the relocated controls, including after narrowing');
    let layoutCases=0;
    for(const width of [1180,900,660])for(const layout of ['studio','focus']){
      await app.evaluate(({BrowserWindow},w)=>BrowserWindow.getAllWindows()[0].setSize(w,720),width);
      await visible('[data-action="view"][data-view="settings"]').click();
      await page.locator('[data-appearance-layout]').selectOption(layout);
      for(const theme of ['sage','midnight','glass','galaxy','aurora','ember']){
        await page.locator(`[data-theme-choice="${theme}"]`).click();
        await visible('[data-action="view"][data-view="session"]').click();
        const bounds=await page.locator('[data-layout]').evaluate(e=>({client:e.clientWidth,scroll:e.scrollWidth}));
        assert.ok(bounds.scroll<=bounds.client+1,JSON.stringify({width,layout,theme,bounds}));
        await page.locator('[data-layout]').evaluate(e=>{e.scrollTop=e.scrollHeight;});
        const emergency=await header.locator('[data-operator="emergency"]').boundingBox();
        const height=await page.evaluate(()=>window.innerHeight);assert.ok(emergency.y>=0&&emergency.y+emergency.height<=height);
        assert.equal(await visible('[data-operator="open"]').isEnabled(),true);
        assert.equal(await input.inputValue(),'Luke 2:9');layoutCases++;
        if(width===1180&&layout==='studio'&&theme==='glass'){
          await page.locator('[data-layout]').evaluate(e=>{e.scrollTop=0;});await page.screenshot({path:path.join(out,'live-default.png')});
        }
        if(width===660&&layout==='focus'&&theme==='glass')await page.screenshot({path:path.join(out,'live-narrow.png')});
        await visible('[data-action="view"][data-view="settings"]').click();
      }
      await visible('[data-action="view"][data-view="session"]').click();
    }
    await page.getByRole('button',{name:'Full transcript',exact:true}).click();
    assert.equal(await page.locator('[data-full-transcript="primary"]').count(),1);assert.equal(await page.locator('[data-full-transcript="secondary"]').count(),1);
    assert.equal(await page.getByRole('button',{name:'Jump to live'}).count(),1);
    await page.getByRole('button',{name:'Focus',exact:true}).click();
    checks.push(`${layoutCases} size/layout/theme cases fit; emergency remains visible at page bottom; both navigation layouts and transcript modes remain usable`);
    await header.locator('[data-operator="emergency"]').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control.state==='stopped'&&window.previewShell.getObserver().session.control.operator.status==='saved',{timeout:30000});
    assert.equal(await accepted(),0);
    await app.close();app=null;
    await launch();
    await page.locator('.vv-recovery-prompt').waitFor();
    await page.locator('[data-operator="recovery"]').click();
    await page.locator('.vv-session-dialog [data-engine-action="restore_session"]').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control.recovery.status==='staged');
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('.vv-recovery-prompt').count(),0);
    assert.equal(await page.evaluate(()=>window.previewShell.getObserver().session.control.state),'stopped');
    checks.push('Emergency save remains acknowledged; restart puts recovery beside Start and Choose session stages Resume without starting STT');
    assert.deepEqual(errors,[]);
    const processInfo=await app.evaluate(({app})=>({packaged:app.isPackaged,executable:process.execPath}));
    fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({result:'PASS',checks,layoutCases,processInfo,backend,errors,
      microphoneSTT:'MOCKED QA callbacks',visibleVerseVIEW:'MOCKED controller',windowsPhysical:'UNVERIFIED'},null,2)+'\n');
    console.log(JSON.stringify({result:'PASS',checks,layoutCases,processInfo},null,2));
    if(process.env.VV_LAYOUT_INSPECT==='1')await new Promise(resolve=>{process.stdin.once('data',resolve);app.once('close',resolve);});
  }catch(e){if(page)await page.screenshot({path:path.join(out,'failure.png')}).catch(()=>{});throw e;}
  finally{
    if(app)await app.close().catch(()=>{});
    if(profile&&path.basename(profile)===tag&&path.basename(path.dirname(profile))==='QA')fs.rmSync(profile,{recursive:true,force:true});
    fs.rmSync(temporary,{recursive:true,force:true});
  }
})().catch(e=>{console.error(e);process.exitCode=1;});
