'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
async function importProfile({reader,manager,commands,sessionId,revision,kind,includeCredentials,chooseFile}){
 if(!['gcp','settings'].includes(kind)||typeof includeCredentials!=='boolean'||!/^[a-f0-9]{32}$/.test(revision||''))throw new Error('Invalid settings import');
 if(kind==='gcp'&&!includeCredentials)throw new Error('Google key import requires explicit credential scope');
 async function current(){const s=await reader.poll(),v=s.session;if(s.connection!=='connected'||v?.session_id!==sessionId||!v.host?.managed||v.pid!==manager.state.pid||!manager.state.owned||manager.state.status!=='ready'||v.control?.state!=='stopped'||v.control.settings?.revision!==revision||!v.control.actions.includes('save_settings'))throw new Error('Settings changed or engine is busy. Reload before importing.');}
 await current();const chosen=await chooseFile({title:kind==='gcp'?'Import Google service-account JSON':'Import VerseView settings',properties:['openFile'],filters:[{name:'JSON',extensions:['json']}]});
 if(chosen.canceled||!chosen.filePaths?.length)return {status:'cancelled',message:'Import cancelled.'};
 const file=chosen.filePaths[0],h=await fs.promises.open(file,fs.constants.O_RDONLY|(fs.constants.O_NOFOLLOW||0));let bytes;
 try{const stat=await h.stat();if(!stat.isFile()||stat.size>512*1024)throw new Error('Choose a JSON file under 512 KB');bytes=await h.readFile();if(bytes.length>512*1024)throw new Error('Import exceeds its limit');try{JSON.parse(bytes.toString('utf8'));}catch{throw new Error('Choose a valid JSON file');}}finally{await h.close();}
 await current();const id=crypto.randomUUID().replaceAll('-',''),directory=path.join(manager.profile,'Imports');await fs.promises.mkdir(directory,{recursive:true,mode:0o700});const stat=await fs.promises.lstat(directory);if(stat.isSymbolicLink()||!stat.isDirectory())throw new Error('Private import store is unavailable');
 const target=path.join(directory,id+'.json');await fs.promises.writeFile(target,JSON.stringify({kind,text:bytes.toString('utf8')}),{mode:0o600,flag:'wx'});
 try{const result=await commands.submit(sessionId,'connection_action',undefined,undefined,undefined,undefined,undefined,{operation:'import',settings_revision:revision,attachment_id:id,include_credentials:includeCredentials});setTimeout(()=>fs.promises.unlink(target).catch(()=>{}),20000).unref();return result;}
 catch(e){await fs.promises.unlink(target).catch(()=>{});throw e;}
}
module.exports={importProfile};
