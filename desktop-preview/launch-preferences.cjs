'use strict';
const fs=require('node:fs'),path=require('node:path');
class LaunchPreference{
 constructor(file,{permission=()=> 'unknown'}={}){this.file=file;this.permission=permission;this.enabled=false;this.claimed=false;try{const v=JSON.parse(fs.readFileSync(file,'utf8'));this.enabled=v.schema===1&&v.enabled===true;}catch{}}
 snapshot(){let permission;try{permission=this.permission();}catch{permission='unknown';}return {enabled:this.enabled,pending:this.enabled&&!this.claimed,permission:['granted','denied','restricted','not-determined','unknown'].includes(permission)?permission:'unknown'};}
 set(enabled){if(typeof enabled!=='boolean')throw new Error('Invalid startup preference');fs.mkdirSync(path.dirname(this.file),{recursive:true,mode:0o700});const temp=this.file+'.tmp';try{fs.writeFileSync(temp,JSON.stringify({schema:1,enabled}),{mode:0o600});fs.renameSync(temp,this.file);}finally{if(fs.existsSync(temp))fs.unlinkSync(temp);}this.enabled=enabled;if(!enabled)this.claimed=true;return this.snapshot();}
 claim(){const state=this.snapshot();this.claimed=true;return {...state,pending:false,claimed:state.pending};}
 cancel(){this.claimed=true;return this.snapshot();}
}
module.exports={LaunchPreference};
