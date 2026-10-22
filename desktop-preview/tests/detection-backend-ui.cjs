'use strict';
// Packaged Electron + owned frozen backend; synthetic QA profile and mocked services.
const {_electron}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const root=path.resolve(__dirname,'..'),output=path.join(root,'test-results','detection-group1');
fs.mkdirSync(output,{recursive:true});
(async()=>{
  assert.ok(process.env.PREVIEW_EXECUTABLE,'Use a packaged app with its frozen backend');
  const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'vv-detection-native-'));
  const source=path.join(temporary,'source'),tag=`detection-native-${process.pid}`;
  fs.mkdirSync(source);
  fs.writeFileSync(path.join(source,'settings.json'),JSON.stringify({language:'English',stt_engine:'deepgram',mic_index:0,
    deepgram_api_key:'SYNTHETIC-ONLY',remote_url:'http://127.0.0.1:50010/control.html',bible_translation:'KJV',
    settings_sync_url:'',auto_save_notes:false,llm_enabled:false,qa_bot_silence:true,manual_confirm:true,verify:true,confidence:.75,
    future_setting:{keep:42}}));
  let app,page,profile;const errors=[],checks=[];
  const expected={confidence:.88,manual_confirm:false,verify:false,verse_interrupt:true,spoken_numeral_mode:true,smart_amen:false};
  async function launch(){
    app=await _electron.launch({executablePath:process.env.PREVIEW_EXECUTABLE,args:[],env:{...process.env,
      VV_PREVIEW_TEST_PROFILE:'1',VV_PREVIEW_TEST_PROFILE_TAG:tag,VV_BACKEND_VERIFY:'1',
      VV_BACKEND_SOURCE_PROFILE:source,VV_OBSERVER_TEST_DIRECTORY:path.join(temporary,'empty')}});
    page=await app.firstWindow();page.on('pageerror',e=>errors.push(e.message));
    profile=await app.evaluate(({app})=>app.getPath('userData'));
    assert.equal(path.basename(profile),tag);assert.equal(path.basename(path.dirname(profile)),'QA');
    const info=await app.evaluate(({app})=>({packaged:app.isPackaged,executable:process.execPath}));
    assert.equal(info.packaged,true);assert.equal(fs.realpathSync(info.executable),fs.realpathSync(process.env.PREVIEW_EXECUTABLE));
    await page.locator('#preview-surface').getByRole('button',{name:'Settings',exact:true}).filter({visible:true}).click();
    await page.locator('[data-consumer-prepare="settings"]').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session?.control?.settings,{timeout:30000});
    const backend=await page.evaluate(()=>window.previewShell.getBackend());
    assert.equal(backend.frozen,true);assert.equal(backend.guiImported,false);assert.equal(backend.verification,true);
    return {info,backend};
  }
  try{
    const first=await launch();
    const field=k=>page.locator(`[data-detector-setting="${k}"]`);
    await field('confidence').fill('88');
    for(const [key,value]of Object.entries(expected))if(key!=='confidence')await field(key).setChecked(value);
    await page.locator('[data-save-settings]').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session.control.settings.values.confidence===.88);
    const disk=()=>JSON.parse(fs.readFileSync(path.join(profile,'Backend','settings.json')));
    for(const [key,value]of Object.entries(expected))assert.equal(disk()[key],value);
    assert.equal(disk().future_setting.keep,42);
    assert.equal(await page.locator('[data-developer-mode]').isChecked(),false);
    checks.push('Normal Settings saves all six detection values through the packaged IPC and actual frozen backend; unknown settings retained');
    await page.getByRole('group',{name:'Detection behavior',exact:true}).screenshot({path:path.join(output,'native-detection-settings.png')});
    await page.locator('#preview-surface').getByRole('button',{name:'Live',exact:true}).filter({visible:true}).click();
    await page.locator('[data-consumer-prepare="start"]').click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session?.control?.state==='running',{timeout:30000});
    await page.waitForFunction(()=>window.previewShell.getObserver().session?.remote_connection?.status==='connected');
    assert.match(await page.locator('[aria-label="VerseVIEW connection"]').textContent(),/connected on attempt 1\/5/);
    await page.locator('[data-live-stop]').first().click();
    await page.waitForFunction(()=>window.previewShell.getObserver().session?.control?.state==='stopped',{timeout:30000});
    checks.push('Frozen engine emits actual new connection telemetry through production publisher/decoder/UI with fake browser transport; explicit Stop completes');
    await app.close();app=null;
    const second=await launch();
    for(const [key,value]of Object.entries(expected)){
      const values=await page.evaluate(()=>window.previewShell.getObserver().session.control.settings.values);
      assert.equal(values[key],value);
      assert.equal(key==='confidence'?Number(await field(key).inputValue())/100:await field(key).isChecked(),value);
    }
    checks.push('All six saved detection settings survive packaged app and backend restart');
    assert.deepEqual(errors,[]);
    fs.writeFileSync(path.join(output,'native-results.json'),JSON.stringify({result:'PASS',first,second,checks,errors,
      microphone:'MOCKED',STT:'MOCKED',presentation:'MOCKED',windowsPhysical:'UNVERIFIED'},null,2)+'\n');
    console.log(JSON.stringify({result:'PASS',checks,executable:first.info.executable},null,2));
  }catch(e){if(page)await page.screenshot({path:path.join(output,'native-failure.png')}).catch(()=>{});throw e;}
  finally{
    if(app)await app.close();
    if(profile&&path.basename(profile)===tag&&path.basename(path.dirname(profile))==='QA')fs.rmSync(profile,{recursive:true,force:true});
    fs.rmSync(temporary,{recursive:true,force:true});
  }
})().catch(e=>{console.error(e);process.exitCode=1;});
