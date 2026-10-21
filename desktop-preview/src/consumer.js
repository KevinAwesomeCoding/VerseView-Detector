(() => {
  'use strict';
  const root=document.getElementById('verseview-prototype');
  let busy=false,notice='',cancelled=false;
  const cancel=()=>{if(busy){cancelled=true;notice='Preparation cancelled. Listening stays stopped.';root.dispatchEvent(new Event('preview:prepare-cancel'));refresh();}};
  const refresh=()=>root.dispatchEvent(new Event('preview:observer'));
  // One user gesture, one launch and one guarded Start. Events wait for readiness;
  // they do not retry commands or bypass sync, recovery or stale-feed checks.
  function waitFor(predicate,timeout=15000){
    if(cancelled)return Promise.reject(new Error('Preparation cancelled. Listening stays stopped.'));
    if(predicate())return Promise.resolve();
    return new Promise((resolve,reject)=>{
      const finish=error=>{clearTimeout(timer);for(const type of ['preview:observer','preview:backend','preview:prepare-cancel'])root.removeEventListener(type,check);error?reject(error):resolve();};
      const check=()=>{if(cancelled)finish(new Error('Preparation cancelled. Listening stays stopped.'));else if(predicate())finish();};
      const timer=setTimeout(()=>finish(new Error('The connection is not ready. Open Settings or try again.')),timeout);
      for(const type of ['preview:observer','preview:backend','preview:prepare-cancel'])root.addEventListener(type,check);
    });
  }
  async function prepare(start){
    if(busy)return;
    cancelled=false;busy=true;notice=start?'Preparing to listen…':'Preparing settings…';refresh();
    try{
      let snapshot=window.previewShell.getObserver();
      if(snapshot.connection!=='connected'||!snapshot.session?.control||snapshot.session.control.state==='closed'){
        const backend=window.previewShell.getBackend();
        if(backend.owned||['starting','closing','ready'].includes(backend.status))throw new Error('The engine connection is unavailable. Check Diagnostics in Developer Mode before trying again.');
        const result=await window.verseviewDesktop.launchBackend();
        if(cancelled)throw new Error('Preparation cancelled. Listening stays stopped.');
        if(result.status!=='ready')throw new Error('The engine could not be prepared. Try again or check Settings.');
        await waitFor(()=>{const s=window.previewShell.getObserver();return s.connection==='connected'&&s.session?.host?.managed&&s.session.pid===result.pid;});
      }
      snapshot=window.previewShell.getObserver();
      if(snapshot.connection!=='connected'||!snapshot.session?.control)throw new Error('The engine connection was lost. Reconnect before trying again.');
      if(!start){notice='Ready. You can configure speech and connections.';return;}
      if(snapshot.session.control.sync?.status==='pulling'){
        notice='Syncing credentials…';refresh();
        const sessionId=snapshot.session.session_id;
        await waitFor(()=>{const s=window.previewShell.getObserver();return s.connection==='connected'&&s.session?.session_id===sessionId&&s.session.control.sync?.status!=='pulling';},30000);
        snapshot=window.previewShell.getObserver();
      }
      if(cancelled||window.previewShell.getMode()!=='observer')throw new Error('Preparation cancelled. Listening stays stopped.');
      const control=snapshot.session.control;
      if(['failed','conflict'].includes(control.sync?.status))throw new Error('Credential sync needs attention. Review Connections in Settings before starting.');
      if(['available','invalid'].includes(control.recovery?.status)){notice='Open Saved sessions on Live to choose Resume or Start new, then press Start listening.';return;}
      if(snapshot.connection!=='connected'||!control.actions.includes('start'))throw new Error('Not ready to listen. Review your speech and connection settings.');
      await window.observerView.start(snapshot);
      notice='Start requested. Waiting for speech readiness.';
    }catch(error){notice=error.message;}
    finally{busy=false;refresh();}
  }
  root.addEventListener('click',event=>{
    if(event.target.closest('[data-consumer-cancel]')){cancel();return;}
    const button=event.target.closest('[data-consumer-prepare]');
    if(button&&!button.disabled&&window.previewShell.getMode()==='observer')prepare(button.dataset.consumerPrepare==='start');
  });
  root.addEventListener('preview:mode',()=>{if(window.previewShell.getMode()!=='observer')cancel();});
  window.consumerFlow=Object.freeze({state:()=>({busy,notice}),prepare,cancel});
})();
