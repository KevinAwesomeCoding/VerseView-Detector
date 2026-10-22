'use strict';
// The renderer supplies an opaque packet identity, never file paths or content.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const MAX_BYTES=8*1024*1024,id=x=>typeof x==='string'&&/^[a-f0-9]{32}$/.test(x);
async function exportSession({reader,manager,sessionId,exportId,chooseDestination,scope='notes'}){
 if(!['notes','connections'].includes(scope))throw new Error('Invalid export scope');
 if(!id(sessionId)||!id(exportId))throw new Error('Invalid session export');
 const current=async()=>{
  const snapshot=await reader.poll(),session=snapshot.session,packet=session?.control?.[scope]?.export;
  if(snapshot.connection!=='connected'||session?.session_id!==sessionId||!session.host?.managed||manager.state.status!=='ready'||!manager.state.owned||session.pid!==manager.state.pid||!packet||packet.id!==exportId)throw new Error('Export session changed or is unavailable. Prepare the export again.');
  return packet;
 };
 const packet=await current(),directory=path.join(manager.profile,'Exports'),file=path.join(directory,exportId+'.txt');
 const stat=await fs.promises.lstat(directory);if(!stat.isDirectory()||stat.isSymbolicLink())throw new Error('Export location is unavailable');
 const fileStat=await fs.promises.lstat(file);if(!fileStat.isFile()||fileStat.isSymbolicLink())throw new Error('Export content is unavailable');
 const handle=await fs.promises.open(file,fs.constants.O_RDONLY|(fs.constants.O_NOFOLLOW||0));let bytes;
 try{const stat=await handle.stat();if(!stat.isFile()||stat.size>MAX_BYTES)throw new Error('Export exceeds its limit');const buffer=Buffer.alloc(MAX_BYTES+1);const result=await handle.read(buffer,0,buffer.length,0);bytes=buffer.subarray(0,result.bytesRead);}finally{await handle.close();}
 if(bytes.length>MAX_BYTES||crypto.createHash('sha256').update(bytes).digest('hex')!==packet.sha256)throw new Error('Export content changed. Prepare it again.');
 const result=await chooseDestination({title:scope==='connections'?'Export settings':'Save captured session',defaultPath:packet.name,filters:[{name:scope==='connections'?'JSON settings':'Text document',extensions:[scope==='connections'?'json':'txt']}],properties:['showOverwriteConfirmation','createDirectory']});
 if(result.canceled||!result.filePath)return {status:'cancelled',message:'Export cancelled. No file was changed.'};
 await current();
 const target=result.filePath,parent=path.dirname(target),temporary=path.join(parent,`.verseview-export-${crypto.randomUUID()}.tmp`);
 try{
  let existing;try{existing=await fs.promises.lstat(target);}catch(e){if(e.code!=='ENOENT')throw e;}
  if(existing?.isSymbolicLink()||existing&&!existing.isFile())throw new Error('Choose a regular file destination');
  const handle=await fs.promises.open(temporary,'wx',0o600);
  try{await handle.writeFile(bytes);await handle.sync();}finally{await handle.close();}
  await fs.promises.rename(temporary,target);
 }catch(error){await fs.promises.unlink(temporary).catch(()=>{});throw new Error('Export was not saved. Existing files were retained.');}
 return {status:'saved',path:target,message:'Saved captured '+packet.kind+' to '+target,bytes:bytes.length,source_id:packet.source_id};
}
module.exports={exportSession};
