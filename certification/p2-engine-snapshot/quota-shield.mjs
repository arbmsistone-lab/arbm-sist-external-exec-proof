import fs from 'node:fs';
import path from 'node:path';

const CRITICAL_RESERVE=0.15;
const NORMAL_RESERVE=0.25;
function ensureDir(file){fs.mkdirSync(path.dirname(file),{recursive:true})}
function read(file){try{return JSON.parse(fs.readFileSync(file,'utf8'))}catch{return {schema:'arbm-quota-shield-v1',providers:{}}}}
function atomic(file,obj){ensureDir(file);const tmp=file+'.tmp-'+process.pid;fs.writeFileSync(tmp,JSON.stringify(obj,null,2)+'\n',{encoding:'utf8',mode:0o600});fs.renameSync(tmp,file);try{fs.chmodSync(file,0o600)}catch{}return obj}
function n(v){const x=Number(v);return Number.isFinite(x)?x:null}
function h(headers,name){try{return headers.get(name)}catch{return null}}
export function quotaFile(dataRoot){return path.join(String(dataRoot),'v11-runtime','quota-shield.json')}
export function recordQuotaHeaders(file,provider,headers){
  const state=read(file),now=new Date().toISOString(),prev=state.providers[provider]||{};
  const limitRequests=n(h(headers,'x-ratelimit-limit-requests')),remainingRequests=n(h(headers,'x-ratelimit-remaining-requests'));
  const limitTokens=n(h(headers,'x-ratelimit-limit-tokens')),remainingTokens=n(h(headers,'x-ratelimit-remaining-tokens'));
  state.providers[provider]={...prev,provider,updatedAt:now,limitRequests:limitRequests??prev.limitRequests??null,remainingRequests:remainingRequests??prev.remainingRequests??null,limitTokens:limitTokens??prev.limitTokens??null,remainingTokens:remainingTokens??prev.remainingTokens??null,resetRequests:h(headers,'x-ratelimit-reset-requests')||prev.resetRequests||'',resetTokens:h(headers,'x-ratelimit-reset-tokens')||prev.resetTokens||'',cooldownUntil:''};
  return atomic(file,state).providers[provider];
}
export function recordQuotaFailure(file,provider,retryAfterSec=180){const state=read(file),prev=state.providers[provider]||{};state.providers[provider]={...prev,provider,updatedAt:new Date().toISOString(),cooldownUntil:new Date(Date.now()+Math.max(60,Number(retryAfterSec)||180)*1000).toISOString(),lastFailure:'RATE_LIMIT'};atomic(file,state);return state.providers[provider]}
export function quotaDecision(file,provider,{critical=false,reservedTokens=0,allowUnknownHardStop=false}={}){
  const state=read(file),q=state.providers[provider];
  if(!q)return allowUnknownHardStop?{eligible:true,state:'ALLOW_HARD_STOP_UNKNOWN',reason:'qualified_hard_stop_no_telemetry'}:{eligible:false,state:'QUOTA_UNKNOWN',reason:'no_telemetry'};
  if(q.cooldownUntil&&Date.parse(q.cooldownUntil)>Date.now())return {eligible:false,state:'COOLDOWN',reason:'rate_limit_cooldown',cooldownUntil:q.cooldownUntil};
  const fractions=[];
  if(q.limitRequests>0&&q.remainingRequests!=null)fractions.push(q.remainingRequests/q.limitRequests);
  if(q.limitTokens>0&&q.remainingTokens!=null)fractions.push(Math.max(0,q.remainingTokens-Math.max(0,Number(reservedTokens)||0))/q.limitTokens);
  if(!fractions.length)return allowUnknownHardStop?{eligible:true,state:'ALLOW_HARD_STOP_UNKNOWN',reason:'qualified_hard_stop_limits_missing'}:{eligible:false,state:'QUOTA_UNKNOWN',reason:'limits_missing'};
  const remainingFraction=Math.max(0,Math.min(...fractions));
  const reserve=critical?CRITICAL_RESERVE:NORMAL_RESERVE;
  if(remainingFraction<=reserve)return {eligible:false,state:critical?'CRITICAL_RESERVE_EXHAUSTED':'RESERVED_FOR_CRITICAL',remainingFraction,reserve};
  return {eligible:true,state:'ALLOW',remainingFraction,reserve,reservedTokens:Math.max(0,Number(reservedTokens)||0)};
}
export function quotaSummary(file){const state=read(file);return {schema:state.schema,providers:Object.fromEntries(Object.entries(state.providers||{}).map(([id,q])=>[id,{...q,normal:quotaDecision(file,id,{critical:false}),critical:quotaDecision(file,id,{critical:true})}]))}}
export const quotaPolicy=Object.freeze({criticalReserve:CRITICAL_RESERVE,normalReserve:NORMAL_RESERVE});
