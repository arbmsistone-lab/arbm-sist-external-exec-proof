import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const MAX_BYTES=4*1024*1024;
const ALLOWED=new Map([
  ['.txt','text/plain'],['.md','text/markdown'],['.json','application/json'],['.csv','text/csv'],
  ['.pdf','application/pdf'],['.docx','application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
  ['.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
  ['.png','image/png'],['.jpg','image/jpeg'],['.jpeg','image/jpeg'],['.webp','image/webp']
]);
function ensure(root){fs.mkdirSync(root,{recursive:true});return path.resolve(root)}
function safeId(v){v=String(v||'');if(!/^[a-f0-9]{24}$/.test(v))throw new Error('invalid_attachment_id');return v}
function sanitizeName(v){const name=path.basename(String(v||'file')).replace(/[\x00-\x1f<>:"/\\|?*]+/g,'_').trim();return (name||'file').slice(0,120)}
function metaDir(root){return path.join(ensure(root),'meta')}
function blobDir(root){return path.join(ensure(root),'blob')}
function metaFile(root,id){return path.join(metaDir(root),safeId(id)+'.json')}
function atomic(file,obj){fs.mkdirSync(path.dirname(file),{recursive:true});const tmp=file+'.tmp-'+process.pid;fs.writeFileSync(tmp,JSON.stringify(obj,null,2)+'\n',{encoding:'utf8',mode:0o600});fs.renameSync(tmp,file);try{fs.chmodSync(file,0o600)}catch{}return obj}
function read(file){try{return JSON.parse(fs.readFileSync(file,'utf8'))}catch{return null}}
function validSignature(ext,buf){
  if(['.txt','.md','.json','.csv'].includes(ext))return true;
  if(ext==='.pdf')return buf.subarray(0,5).toString('ascii')==='%PDF-';
  if(ext==='.png')return buf.length>=8&&buf.subarray(0,8).equals(Buffer.from('89504e470d0a1a0a','hex'));
  if(ext==='.jpg'||ext==='.jpeg')return buf.length>=3&&buf[0]===0xff&&buf[1]===0xd8&&buf[2]===0xff;
  if(ext==='.webp')return buf.length>=12&&buf.subarray(0,4).toString('ascii')==='RIFF'&&buf.subarray(8,12).toString('ascii')==='WEBP';
  if(ext==='.docx'||ext==='.xlsx')return buf.length>=4&&buf[0]===0x50&&buf[1]===0x4b&&[0x03,0x05,0x07].includes(buf[2]);
  return false;
}
export function createAttachment(root,{name,mime,dataBase64}={}){
  const clean=sanitizeName(name),ext=path.extname(clean).toLowerCase();
  const expected=ALLOWED.get(ext);if(!expected)throw new Error('attachment_type_not_allowed');
  const supplied=String(mime||expected).toLowerCase();if(supplied!==expected&&!(expected==='image/jpeg'&&supplied==='image/jpg'))throw new Error('attachment_mime_mismatch');
  let buf;try{buf=Buffer.from(String(dataBase64||''),'base64')}catch{throw new Error('attachment_invalid_base64')}
  if(!buf.length)throw new Error('attachment_empty');if(buf.length>MAX_BYTES)throw new Error('attachment_too_large');if(!validSignature(ext,buf))throw new Error('attachment_signature_mismatch');
  const id=crypto.randomBytes(12).toString('hex'),createdAt=new Date().toISOString();
  fs.mkdirSync(blobDir(root),{recursive:true});const blob=path.join(blobDir(root),id+ext);
  fs.writeFileSync(blob,buf,{mode:0o600});try{fs.chmodSync(blob,0o600)}catch{}
  const sha256=crypto.createHash('sha256').update(buf).digest('hex');
  return atomic(metaFile(root,id),{id,name:clean,mime:expected,ext,size:buf.length,sha256,createdAt,chatIds:[]});
}
export function readAttachment(root,id){return read(metaFile(root,id))}
export function attachmentPreview(root,id,{maxChars=24000}={}){
  const meta=readAttachment(root,id);if(!meta)throw new Error('attachment_not_found');
  const textExt=new Set(['.txt','.md','.json','.csv']);
  if(!textExt.has(meta.ext))return {id:meta.id,name:meta.name,mime:meta.mime,size:meta.size,sha256:meta.sha256,previewable:false,text:''};
  const blob=path.join(blobDir(root),meta.id+meta.ext);const text=fs.readFileSync(blob,'utf8').slice(0,Math.max(0,Math.min(Number(maxChars)||24000,48000)));
  return {id:meta.id,name:meta.name,mime:meta.mime,size:meta.size,sha256:meta.sha256,previewable:true,text};
}
export function listAttachments(root){
  fs.mkdirSync(metaDir(root),{recursive:true});
  return fs.readdirSync(metaDir(root)).filter(x=>/^[a-f0-9]{24}\.json$/.test(x)).map(x=>read(path.join(metaDir(root),x))).filter(Boolean).sort((a,b)=>String(b.createdAt).localeCompare(String(a.createdAt)));
}
export function linkAttachment(root,id,chatId){const meta=readAttachment(root,id);if(!meta)throw new Error('attachment_not_found');const cid=String(chatId||'');if(!/^[a-f0-9]{24}$/.test(cid))throw new Error('invalid_chat_id');meta.chatIds=Array.isArray(meta.chatIds)?meta.chatIds:[];if(!meta.chatIds.includes(cid))meta.chatIds.push(cid);return atomic(metaFile(root,id),meta)}
export function removeAttachment(root,id){const meta=readAttachment(root,id);if(!meta)return false;try{fs.unlinkSync(path.join(blobDir(root),id+meta.ext))}catch{}try{fs.unlinkSync(metaFile(root,id))}catch{}return true}
export function validateAttachmentIds(root,ids=[],chatId=''){const unique=[...new Set((Array.isArray(ids)?ids:[]).map(String))].slice(0,6);return unique.map(id=>{const meta=readAttachment(root,id);if(!meta)throw new Error('attachment_not_found');if(chatId&&!Array.isArray(meta.chatIds)||chatId&&!meta.chatIds.includes(chatId))throw new Error('attachment_not_linked_to_chat');return {id:meta.id,name:meta.name,mime:meta.mime,size:meta.size,sha256:meta.sha256}})}
export const attachmentLimits=Object.freeze({maxBytes:MAX_BYTES,maxPerMessage:6,allowedExtensions:[...ALLOWED.keys()]});
