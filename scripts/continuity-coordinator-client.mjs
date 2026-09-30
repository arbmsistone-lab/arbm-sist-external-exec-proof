// OIDC stays in this closure; errors never include response bodies or credentials.
export function createCoordinatorClient({url,initialToken='',env=process.env,fetchImpl=fetch,timeoutMs=15000}={}) {
  let token=String(initialToken).trim(), refreshing=null;
  async function freshToken() {
    if(!refreshing) refreshing=(async()=>{
      const endpoint=env.ACTIONS_ID_TOKEN_REQUEST_URL;
      const credential=env.ACTIONS_ID_TOKEN_REQUEST_TOKEN;
      if(!endpoint||!credential)throw new Error('continuity_oidc_refresh_unavailable');
      let oidcUrl;
      try {oidcUrl=new URL(endpoint);oidcUrl.searchParams.set('audience','arbm-continuity');}
      catch {throw new Error('continuity_oidc_endpoint_invalid');}
      if(oidcUrl.protocol!=='https:')throw new Error('continuity_oidc_endpoint_invalid');
      let response;
      try {response=await fetchImpl(oidcUrl.href,{headers:{authorization:`Bearer ${credential}`},redirect:'error',signal:AbortSignal.timeout(timeoutMs)});}
      catch {throw new Error('continuity_oidc_request_failed');}
      if(!response.ok)throw new Error(`continuity_oidc_http_${response.status}`);
      let body;
      try {body=await response.json();}catch {throw new Error('continuity_oidc_invalid_response');}
      if(typeof body?.value!=='string'||!body.value.trim()||/\s/.test(body.value))throw new Error('continuity_oidc_invalid_token');
      token=body.value;
      return token;
    })().finally(()=>{refreshing=null;});
    return refreshing;
  }
  return async function call(action,payload={}) {
    if(!/^[a-z_]+$/.test(action))throw new Error('continuity_invalid_action');
    // Serialize once, so a 401 retry carries the identical action and payload.
    const requestBody=JSON.stringify({action,...payload});
    if(!token)await freshToken();
    for(let attempt=0;attempt<2;attempt++) {
      const usedToken=token;
      let response;
      try {response=await fetchImpl(url,{method:'POST',headers:{authorization:`Bearer ${usedToken}`,'content-type':'application/json'},body:requestBody,redirect:'error',signal:AbortSignal.timeout(timeoutMs)});}
      catch {throw new Error(`continuity_${action}_request_failed`);}
      if(response.status===401&&attempt===0) {
        // Another call may already have replaced the rejected token.
        if(token===usedToken)await freshToken();
        continue;
      }
      if(!response.ok)throw new Error(`continuity_${action}_http_${response.status}`);
      try {return await response.json();}catch {throw new Error(`continuity_${action}_invalid_response`);}
    }
  };
}
