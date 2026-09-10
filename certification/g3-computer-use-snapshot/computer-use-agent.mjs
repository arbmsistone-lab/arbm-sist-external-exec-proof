import crypto from 'node:crypto';
import {captureComputerState,verifyComputerTransition,actionDecision} from './computer-use-verifier.mjs';
const hash=v=>crypto.createHash('sha256').update(JSON.stringify(v??null)).digest('hex');
export function compileComputerMission({objective='',maxSteps=20,goal={},risk='LOW'}={}){
  if(!String(objective).trim())throw new Error('objective_required');
  const cap=Math.max(1,Math.min(100,Number(maxSteps)||20));
  return {schema:'arbm-computer-mission-v1',objective:String(objective),maxSteps:cap,goal,risk:String(risk).toUpperCase(),sha256:hash({objective,maxSteps:cap,goal,risk})};
}
export function goalReached(state,goal={}){
  if(goal.urlIncludes&&!String(state.url||'').includes(goal.urlIncludes))return false;
  if(goal.titleIncludes&&!String(state.title||'').includes(goal.titleIncludes))return false;
  if(goal.appStateSha256&&state.appStateSha256!==goal.appStateSha256)return false;
  return Boolean(goal.urlIncludes||goal.titleIncludes||goal.appStateSha256);
}
export async function runComputerMission({mission,observe,plan,act,recover,approve,maxRecovery=2,onEvent=()=>{}}={}){
  if(!mission||!observe||!plan||!act)throw new Error('invalid_agent_contract');
  let before=captureComputerState(await observe()),recoveries=0;const trace=[];
  for(let step=0;step<mission.maxSteps;step++){
    if(goalReached(before,mission.goal))return {state:'SUCCEEDED',steps:step,recoveries,trace,final:before};
    const proposed=await plan({mission,state:before,step,trace});if(!proposed?.type)throw new Error('action_required');
    const actionSignature=hash([proposed.type,proposed.target,proposed.value]);
    const proposedRisk=String(proposed.risk||mission.risk||'LOW').toUpperCase();
    if(['HIGH','CRITICAL'].includes(proposedRisk)){const decision=typeof approve==='function'?await approve({mission,step,action:proposed,actionSignature,risk:proposedRisk}):false;if(decision!==true){await onEvent({type:'ACTION_APPROVAL_REQUIRED',step,action:proposed,actionSignature,risk:proposedRisk});return {state:'APPROVAL_REQUIRED',steps:step,recoveries,trace,final:before,action:proposed,actionSignature};}}
    const repeated=trace.slice(-3).filter(x=>x.actionSignature===actionSignature).length;
    if(repeated>=3)return {state:'LOOP_BLOCKED',steps:step,recoveries,trace,final:before};
    await onEvent({type:'ACTION_PLANNED',step,action:proposed});const result=await act(proposed);const after=captureComputerState(await observe());
    const verification=verifyComputerTransition(before,after,proposed.verify||{});const decision=actionDecision({risk:proposed.risk||mission.risk,verification});
    trace.push({step,action:proposed,actionSignature,result,verification,before:before.evidenceSha256,after:after.evidenceSha256});await onEvent({type:'ACTION_VERIFIED',step,decision,verification});
    if(decision.state==='VERIFIED'){before=after;recoveries=0;continue;}
    if(decision.state==='REVIEW_REQUIRED')return {state:'REVIEW_REQUIRED',steps:step+1,recoveries,trace,final:after};
    if(!recover||recoveries>=maxRecovery)return {state:'RECOVERY_EXHAUSTED',steps:step+1,recoveries,trace,final:after};
    recoveries++;await recover({mission,step,action:proposed,before,after,verification,recoveries});before=captureComputerState(await observe());
    if(step+1>=mission.maxSteps)return {state:'RECOVERY_EXHAUSTED',steps:step+1,recoveries,trace,final:before};
  }
  return {state:goalReached(before,mission.goal)?'SUCCEEDED':'STEP_LIMIT',steps:mission.maxSteps,recoveries,trace,final:before};
}
