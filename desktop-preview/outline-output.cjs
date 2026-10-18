'use strict';

// Explicit, same-app outline output. Dependencies are injected so native display
// routing can be checked without opening an audience-facing window in tests.
class OutlineOutput {
  constructor({BrowserWindow,screen,readSnapshot,page,preload,onChange=()=>{}}) {
    Object.assign(this,{BrowserWindow,screen,readSnapshot,page,preload,onChange});
    this.window=null;this.identity=null;this.lastRevision=null;
    this.message='';
  }
  displays() {
    return this.screen.getAllDisplays().filter(d=>Number.isSafeInteger(d.id)).map(d=>({id:String(d.id),
      label:typeof d.label==='string'&&d.label?d.label.slice(0,80):`Display ${d.id}`,
      width:d.bounds.width,height:d.bounds.height,primary:d.id===this.screen.getPrimaryDisplay().id}));
  }
  state() {
    return {open:!!this.window&&!this.window.isDestroyed(),sessionId:this.identity?.sessionId||null,
      target:this.identity?.target||null,displays:this.displays(),message:this.message};
  }
  async open(sessionId,target) {
    if(typeof target!=='string'||(!/^-?\d{1,16}$/.test(target)&&target!=='windowed'))throw new Error('Invalid outline display target');
    const snapshot=await this.readSnapshot(),session=snapshot.session;
    const age=Date.now()-Date.parse(session?.updated_at);
    if(snapshot.connection!=='connected'||session?.session_id!==sessionId||!session.control?.outline
      ||!Number.isFinite(age)||age>6000||age< -10000)throw new Error('Outline session unavailable; refresh before opening output');
    const displays=this.screen.getAllDisplays();
    const display=target==='windowed'?this.screen.getPrimaryDisplay():displays.find(d=>String(d.id)===target);
    if(!display)throw new Error('Selected display is no longer connected');
    this.close();
    this.identity={sessionId,controlId:session.control.id,target};
    const windowed=target==='windowed',area=display.workArea||display.bounds;
    const output=this.window=new this.BrowserWindow({title:'Live Sermon Points',show:false,frame:windowed,
      x:windowed?area.x:display.bounds.x,y:windowed?area.y:display.bounds.y,
      width:windowed?Math.min(800,area.width):display.bounds.width,
      height:windowed?Math.min(600,area.height):display.bounds.height,backgroundColor:'#0d0d0d',
      webPreferences:{preload:this.preload,nodeIntegration:false,contextIsolation:true,sandbox:true,
        webSecurity:true,spellcheck:false,devTools:false}});
    output.webContents.setWindowOpenHandler(()=>({action:'deny'}));
    output.webContents.on('will-navigate',event=>event.preventDefault());
    output.webContents.on('will-attach-webview',event=>event.preventDefault());
    output.webContents.on('before-input-event',(_event,input)=>{if(input.key==='Escape')this.close();});
    output.webContents.on('did-finish-load',async()=>{
      try{
        const latest=await this.readSnapshot();
        if(this.window===output){this.lastRevision=null;this.update(latest);}
      }catch{if(this.window===output)this.close();}
    });
    output.once('ready-to-show',()=>{
      if(this.window!==output||output.isDestroyed())return;
      if(!windowed)output.setFullScreen(true);
      output.show();
    });
    output.once('closed',()=>{
      if(this.window!==output)return;
      this.window=null;this.identity=null;this.lastRevision=null;this.onChange(this.state());
    });
    Promise.resolve(output.loadFile(this.page)).catch(()=>{
      if(this.window===output)this.close('Could not load the outline window.');
    });
    this.onChange(this.state());
    return this.state();
  }
  update(snapshot) {
    if(!this.window||this.window.isDestroyed())return;
    const session=snapshot.session;
    if(snapshot.connection!=='connected'||session?.session_id!==this.identity.sessionId
      ||session.control?.id!==this.identity.controlId||!session.control.outline){this.close('Outline session changed or its feed is unavailable.');return;}
    if(this.identity.target!=='windowed'&&!this.screen.getAllDisplays().some(d=>String(d.id)===this.identity.target)){this.close('Selected display disconnected.');return;}
    const outline=session.control.outline;
    if(outline.revision!==this.lastRevision){
      this.lastRevision=outline.revision;
      this.window.webContents.send('preview:outline-text',{text:typeof outline.text==='string'?outline.text.slice(0,4000):''});
    }
  }
  close(message='') {
    this.message=message;
    const output=this.window;this.window=null;this.identity=null;this.lastRevision=null;
    if(output&&!output.isDestroyed())output.close();
    if(output)this.onChange(this.state());
    return this.state();
  }
}
module.exports={OutlineOutput};
