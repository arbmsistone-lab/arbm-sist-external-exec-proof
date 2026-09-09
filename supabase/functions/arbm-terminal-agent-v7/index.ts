import "jsr:@supabase/functions-js@2.116.0/edge-runtime.d.ts";
import { createRemoteJWKSet, jwtVerify } from "npm:jose@5.10.0";

const ISS = "https://token.actions.githubusercontent.com";
const AUD = "arbm-sist-benchmark";
const REPO = "arbmsistone-lab/arbm-sist-external-exec-proof";
const JWKS = createRemoteJWKSet(new URL(ISS + "/.well-known/jwks"));
const GEMINI_STRONG = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash"];
const GEMINI_EFFICIENT = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"];
const GEMINI_MODELS = [...GEMINI_STRONG, ...GEMINI_EFFICIENT];
const GROQ_STRONG = ["qwen/qwen3.8-27b", "openai/gpt-oss-120b"];
const GROQ_EFFICIENT = ["qwen/qwen3.6-27b", "openai/gpt-oss-20b"];
const GROQ_MODELS = [...GROQ_STRONG, ...GROQ_EFFICIENT];
const GROQ_URL = "https://api.groq.com/openai/v1/chat/completions";
const LIGHTNING_URL = "https://lightning.ai/api/v1/chat/completions";
const LIGHTNING_MODELS = ["lightning-ai/gpt-oss-20b", "lightning-ai/gpt-oss-120b", "lightning-ai/nemotron-3-ultra-550b-a55b"];
const MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions";
const MISTRAL_MODELS = ["ministral-3b-latest", "ministral-8b-latest", "mistral-small-latest"];
const COOLDOWN = new Map<string, number>();
const cooling = (k:string) => (COOLDOWN.get(k) || 0) > Date.now();
const waitMs = (v:string|null, fallback=60) => { const m=/([0-9.]+)/.exec(String(v||"")); return Math.max(1000, (m ? Number(m[1]) : fallback) * 1000); };
const cool = (k:string, v:string|null, fallback=60) => COOLDOWN.set(k, Date.now()+waitMs(v,fallback));
const scrub = (v:unknown) => {
  let text=String(v||"");
  for (const name of ["MISTRAL_API_KEY","GROQ_API_KEY","GEMINI_API_KEY","LIGHTNING_API_KEY","SUPABASE_SERVICE_ROLE_KEY"]) {
    const secret=Deno.env.get(name); if(secret) text=text.split(secret).join("[redacted]");
  }
  return text.replace(/Bearer\s+[^\s"']+/gi,"Bearer [redacted]").replace(/org_[A-Za-z0-9_-]+/g,"[redacted]").slice(0,220);
};
const hashText = (v:string) => { let h=2166136261; for (let i=0;i<v.length;i++) h=Math.imul(h^v.charCodeAt(i),16777619); return h>>>0; };
const rotate = <T>(xs:T[], seed:number) => xs.length ? xs.slice(seed%xs.length).concat(xs.slice(0,seed%xs.length)) : xs;
const ranked = <T>(efficient:T[], strong:T[], step:number, prompt:string) => { const seed=hashText(prompt)+step; const first=step<=2?efficient:strong, second=step<=2?strong:efficient; return [...rotate(first,seed),...rotate(second,seed>>>1)]; };

const schema = {
  type: "object",
  additionalProperties: false,
  properties: {
    action: { type: "string", enum: ["exec", "finish"] },
    command: { type: "string" },
    summary: { type: "string" }
  },
  required: ["action", "command", "summary"]
};

const respond = (x: unknown, status = 200) => new Response(JSON.stringify(x), {
  status,
  headers: { "content-type": "application/json", "cache-control": "no-store" }
});
async function auth(req: Request) {
  const match = /^Bearer\s+(.+)$/i.exec(req.headers.get("authorization") || "");
  if (!match) throw new Error("OIDC_MISSING");
  const { payload } = await jwtVerify(match[1], JWKS, {
    issuer: ISS,
    audience: AUD,
    algorithms: ["RS256"]
  });
  if (payload.repository !== REPO) throw new Error("OIDC_REPOSITORY");
  const ref = String(payload.ref || "");
  if (!(ref.startsWith("refs/heads/p3/terminal-bench-") || (ref.startsWith("refs/heads/codex/terminal-capacity-") || ref.startsWith("refs/heads/codex/free-capacity-")))) throw new Error("OIDC_REF");
  if (!["push", "workflow_dispatch"].includes(String(payload.event_name || ""))) {
    throw new Error("OIDC_EVENT");
  }
  return { runId: String(payload.run_id || ""), sha: String(payload.sha || ""), ref };
}

function parseJson(text: string) {
  const clean = String(text || "").trim()
    .replace(/^```(?:json)?\s*/i, "")
    .replace(/\s*```$/i, "");
  try { return JSON.parse(clean); } catch {}
  const a=clean.indexOf("{"); const b=clean.lastIndexOf("}");
  if(a>=0 && b>a){ try { return JSON.parse(clean.slice(a,b+1)); } catch {} }
  return null;
}

function extractGemini(raw: any) {
  return (raw?.candidates?.[0]?.content?.parts || []).map((p: any) => p?.text || "").join("");
}
function googleQuota(raw:any){ let retry="", limit:any=null, metric=""; for(const d of (raw?.error?.details||[])){ if(d?.retryDelay) retry=String(d.retryDelay); const v=d?.violations?.[0]; if(v){ limit=v?.quotaValue ?? null; metric=(String(v?.quotaId||v?.quotaMetric||"").split("/").pop() || "").slice(0,120); } } return {retry,limit,metric}; }
async function callGemini(prompt: string, step = 1, modelHint = "") {
  const key = String(Deno.env.get("GEMINI_API_KEY") || "").trim();
  if (!key) return { result: null, attempts: [{ route: "google", status: "not_configured" }] };
  const attempts: any[] = [];
  const models = modelHint && GEMINI_MODELS.includes(modelHint) ? [modelHint] : ranked(GEMINI_EFFICIENT,GEMINI_STRONG,step,prompt);
  for (const model of models.slice(0, 3)) {
    if (cooling("google:"+model)) { attempts.push({ route: "google", model, status: "cooldown" }); continue; }
    try {
      const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`, {
        method: "POST",
        headers: { "content-type": "application/json", "x-goog-api-key": key },
        body: JSON.stringify({
          contents: [{ parts: [{ text: prompt }] }],
          generationConfig: {
            maxOutputTokens: 192,
            responseMimeType: "application/json",
            responseJsonSchema: schema
          }
        }),
        signal: AbortSignal.timeout(10000)
      });
      const raw = await res.json().catch(() => ({}));
      const action = res.ok ? parseJson(extractGemini(raw)) : null;
      const quota=googleQuota(raw), retry=quota.retry || res.headers.get("retry-after");
      if (res.status === 429 || res.status === 503) cool("google:"+model, retry, res.status===429 ? 120 : 30);
      attempts.push({ route: "google", model, status: res.status, parsed: !!action, usage_tokens: Number.isFinite(raw?.usageMetadata?.totalTokenCount) ? raw.usageMetadata.totalTokenCount : null, retry_after: retry || null, quota_limit: quota.limit, quota_metric: quota.metric || null });
      if (action) return { result: { action, model, provider: "google-gemini" }, attempts };
      if (!mistralModelUnavailable(res.status, String(raw?.error?.message || ""))) break;
    } catch (error: any) {
      attempts.push({ route: "google", model, status: "transport", error: String(error?.name || "Error") });
      break;
    }
  }
  return { result: null, attempts };
}
async function callGroq(prompt: string, step = 1, modelHint = "") {
  const key = String(Deno.env.get("GROQ_API_KEY") || "").trim();
  if (!key) return { result: null, attempts: [{ route: "groq", status: "not_configured" }] };
  const attempts: any[] = [];
  const system = "You are ARBM SIST in a Terminal-Bench sandbox. No tools are available. Never emit tool calls. Output exactly one JSON object with keys action, command, summary. action must be exec or finish.";
  const models = modelHint && GROQ_MODELS.includes(modelHint) ? [modelHint] : ranked(GROQ_EFFICIENT,GROQ_STRONG,step,prompt);
  for (const model of models.slice(0, 3)) {
    if (cooling("groq:"+model)) { attempts.push({ route: "groq", model, status: "cooldown" }); continue; }
    for (const structured of [true, false]) {
      try {
        const payload:any = { model, messages: [{ role: "system", content: system }, { role: "user", content: prompt }], max_completion_tokens: 192 };
        if (structured) payload.response_format = { type: "json_object" };
        const res = await fetch(GROQ_URL, { method: "POST", headers: { "content-type": "application/json", authorization: `Bearer ${key}` }, body: JSON.stringify(payload), signal: AbortSignal.timeout(10000) });
        const raw = await res.json().catch(() => ({}));
        const action = res.ok ? parseJson(String(raw?.choices?.[0]?.message?.content || "")) : null;
        const rpd = res.headers.get("x-ratelimit-limit-requests"), tpm = res.headers.get("x-ratelimit-limit-tokens");
        const retryAfter = res.headers.get("retry-after") || res.headers.get("x-ratelimit-reset-tokens");
        const remainingReq = res.headers.get("x-ratelimit-remaining-requests"), remainingTokens = res.headers.get("x-ratelimit-remaining-tokens");
        if (res.status === 429 || remainingTokens === "0") cool("groq:"+model, retryAfter, 60);
        const freePlanProven = rpd === "1000" && tpm === "8000";
        attempts.push({ route: structured ? "groq-json-object" : "groq-json-text", model, status: res.status, parsed: !!action, usage_tokens: Number.isFinite(raw?.usage?.total_tokens) ? raw.usage.total_tokens : null, free_plan_proven: freePlanProven, rate_limit_rpd: rpd, rate_limit_tpm: tpm, retry_after: retryAfter, remaining_requests: remainingReq, remaining_tokens: remainingTokens, error_message: scrub(raw?.error?.message) });
        if (action && freePlanProven) return { result: { action, model, provider: "groqcloud-free" }, attempts };
        if ([401,403,429].includes(res.status) || res.status >= 500) return {result:null,attempts};
        if (structured && res.status === 400 && /response.?format|json.?object/i.test(String(raw?.error?.message || ""))) continue;
        break;
      } catch (error: any) {
        attempts.push({ route: structured ? "groq-json-object" : "groq-json-text", model, status: "transport", error: String(error?.name || "Error") });
        return {result:null,attempts};
      }
    }
    const last = attempts[attempts.length-1];
    if (!mistralModelUnavailable(last?.status, String(last?.error_message || ""))) break;
  }
  return { result: null, attempts };
}
async function callLightning(prompt: string, step = 1, modelHint = "") {
  const storedKey = String(Deno.env.get("LIGHTNING_API_KEY") || "").trim();
  const key = storedKey.split("/")[0];
  const hardFree = String(Deno.env.get("ARBM_LIGHTNING_ZERO_SPEND_CONFIRMED") || "") === "1";
  if (!key) return { result: null, attempts: [{ route: "lightning", status: "not_configured" }] };
  if (!hardFree) return { result: null, attempts: [{ route: "lightning", status: "zero_spend_unconfirmed" }] };
  const attempts: any[] = [];
  const models = modelHint && LIGHTNING_MODELS.includes(modelHint) ? [modelHint] : (step <= 2 ? LIGHTNING_MODELS : [LIGHTNING_MODELS[1], LIGHTNING_MODELS[2], LIGHTNING_MODELS[0]]);
  const system = "You are ARBM SIST in a Terminal-Bench sandbox. Return exactly one JSON object with keys action, command, summary. action must be exec or finish.";
  for (const model of models.slice(0, 3)) {
    if (cooling("lightning:"+model)) { attempts.push({ route: "lightning", model, status: "cooldown" }); continue; }
    try {
      const res = await fetch(LIGHTNING_URL, { method: "POST", headers: { "content-type": "application/json", authorization: `Bearer ${key}` }, body: JSON.stringify({ model, messages: [{role:"system",content:system},{role:"user",content:prompt}], max_tokens:192, temperature:0 }), signal: AbortSignal.timeout(10000) });
      const raw = await res.json().catch(() => ({}));
      const action = res.ok ? parseJson(String(raw?.choices?.[0]?.message?.content || "")) : null;
      if (res.status === 429) cool("lightning:"+model, res.headers.get("retry-after"), 60);
      attempts.push({ route: "lightning-free", model, status: res.status, parsed: !!action, usage_tokens: Number.isFinite(raw?.usage?.total_tokens) ? raw.usage.total_tokens : null, error_message: scrub(raw?.error?.message) });
      if (action) return { result: { action, model, provider: "lightning-ai-free" }, attempts };
      if (!mistralModelUnavailable(res.status, String(raw?.error?.message || ""))) break;
    } catch (error:any) { attempts.push({ route:"lightning-free", model, status:"transport", error:String(error?.name||"Error") }); break; }
  }
  return { result: null, attempts };
}
function mistralRetryMs(value: string | null, now = Date.now()) {
  if (!value) return 120000;
  const seconds = Number(value);
  if (Number.isFinite(seconds) && seconds >= 0) return Math.max(1000, seconds * 1000);
  const date = Date.parse(value);
  return Number.isFinite(date) ? Math.max(1000, date - now) : 120000;
}
function mistralLimitHeaders(headers: Headers) {
  const limits: Record<string, string> = {};
  headers.forEach((value, name) => {
    if (/^(?:x-)?rate-?limit(?:-[a-z-]+)?$/.test(name) && /^[0-9.,;= :a-zA-Z_"/+-]{1,220}$/.test(value)) {
      limits[name] = value;
    }
  });
  return limits;
}
function mistralModelUnavailable(status: number, message: string) {
  return [400,404,422].includes(status) && /model/i.test(message) &&
    /not found|does not exist|unavailable|not available|unsupported|invalid model/i.test(message);
}
async function callMistral(prompt: string, modelHint = "") {
  const key = String(Deno.env.get("MISTRAL_API_KEY") || "").trim();
  const hardFree = Deno.env.get("ARBM_MISTRAL_ZERO_SPEND_CONFIRMED") === "1";
  const liveProven = Deno.env.get("ARBM_MISTRAL_LIVE_PROVEN") === "1";
  // This service supports only HARD mode. Missing env retains the existing hard-only policy.
  const hardMode = (Deno.env.get("ZERO_SPEND_MODE") || "HARD") === "HARD";
  const blocked = (status: string) => ({ result: null, attempts: [{route:"mistral",status,mandatory_cost_usd:0,paid_fallback_used:false}] });
  if (!key) return blocked("not_configured");
  if (!hardFree || !hardMode) return blocked("zero_spend_unconfirmed");
  if (modelHint && !MISTRAL_MODELS.includes(modelHint)) return blocked("invalid_model_hint");
  if (!liveProven && !modelHint) return blocked("live_proof_required");
  if (cooling("mistral")) return blocked("cooldown");
  const attempts: any[] = [];
  const models = modelHint ? [modelHint] : MISTRAL_MODELS;
  const system = "Return exactly one JSON object with keys action, command, summary. action must be exec or finish.";
  for (const model of models.slice(0, 3)) {
    try {
      const res = await fetch(MISTRAL_URL, {method:"POST",headers:{"content-type":"application/json",authorization:`Bearer ${key}`},body:JSON.stringify({model,messages:[{role:"system",content:system},{role:"user",content:prompt}],max_tokens:192,response_format:{type:"json_object"}}),signal:AbortSignal.timeout(10000)});
      const raw = await res.json().catch(() => ({}));
      const parsed = res.status === 200 ? parseJson(String(raw?.choices?.[0]?.message?.content || "")) : null;
      const action = parsed && ["exec","finish"].includes(parsed.action) && typeof parsed.command === "string" && typeof parsed.summary === "string" && (parsed.action !== "exec" || parsed.command.trim()) ? parsed : null;
      const message = scrub(String(raw?.message || raw?.error?.message || "").split(key).join("[redacted]"));
      const retry = res.headers.get("retry-after");
      const limits = mistralLimitHeaders(res.headers);
      const tokens = Number.isFinite(raw?.usage?.total_tokens) && raw.usage.total_tokens >= 0 ? raw.usage.total_tokens : null;
      if (res.status === 429 || Object.entries(limits).some(([name,value]) => name.includes("remaining") && value === "0")) {
        COOLDOWN.set("mistral", Date.now() + mistralRetryMs(retry));
      } else if (res.status >= 500) {
        COOLDOWN.set("mistral", Date.now() + Math.max(30000, mistralRetryMs(retry)));
      }
      attempts.push({route:"mistral-free",model,status:res.status,parsed:!!action,usage_tokens:tokens,usage:{total_tokens:tokens},retry_after:retry,rate_limit_remaining:limits["x-ratelimit-remaining"] ?? limits["ratelimit-remaining"] ?? null,rate_limit_headers:limits,mandatory_cost_usd:0,paid_fallback_used:false,error_message:message});
      if (action) return {result:{action,model,provider:"mistral-free"},attempts};
      // Do not rotate models on account quotas, auth failures, outages or malformed output.
      if (!mistralModelUnavailable(res.status, message)) break;
    } catch (error: any) {
      COOLDOWN.set("mistral", Date.now() + 30000);
      attempts.push({route:"mistral-free",model,status:"transport",parsed:false,mandatory_cost_usd:0,paid_fallback_used:false,error:String(error?.name || "Error")});
      break;
    }
  }
  return {result:null,attempts};
}
async function callCloudflare(prompt: string, modelHint = "") {
  const url = String(Deno.env.get("ARBM_CF_AI_URL") || "").trim();
  const secret = String(Deno.env.get("ARBM_CF_AI_SHARED_SECRET") || "").trim();
  if (!url || !secret) return { result: null, attempts: [{ route: "cloudflare", status: "not_configured" }] };
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json", "x-arbm-ai-secret": secret },
      body: JSON.stringify({
        system: "You are ARBM SIST inside a Terminal-Bench sandbox. Return only JSON matching the supplied schema.",
        input: prompt,
        mode: "json",
        schema,
        ...(modelHint ? { model: modelHint } : {})
      }),
      signal: AbortSignal.timeout(25000)
    });
    const raw = await res.text();
    if (!res.ok) return { result: null, attempts: [{ route: "cloudflare", status: res.status, error_message: scrub(raw) }] };
    const outer = JSON.parse(raw);
    const action = parseJson(String(outer?.output || ""));
    const attempt = { route: "cloudflare", status: res.status, model: String(outer?.model || "unknown"), parsed: !!action };
    if (action) {
      return {
        result: { action, model: String(outer?.model || "cloudflare-free"), provider: String(outer?.provider || "cloudflare-workers-ai") },
        attempts: [attempt]
      };
    }
    return { result: null, attempts: [attempt] };
  } catch (error: any) {
    return { result: null, attempts: [{ route: "cloudflare", status: "transport", error: String(error?.name || "Error") }] };
  }
}
async function meshRpc(name: string, body: Record<string,unknown>) {
  const url=Deno.env.get("SUPABASE_URL"), key=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  if (!url || !key) throw new Error("SHARED_CONTROL_UNAVAILABLE");
  const response=await fetch(url+"/rest/v1/rpc/"+name,{method:"POST",headers:{"content-type":"application/json",apikey:key,authorization:`Bearer ${key}`},body:JSON.stringify(body),signal:AbortSignal.timeout(4000)});
  if(!response.ok) throw new Error("SHARED_CONTROL_UNAVAILABLE");
  return await response.json();
}
async function controlled(provider:string,prompt:string,call:()=>Promise<any>) {
  const started=Date.now();
  // UTF-8 bytes plus protocol/output allowance, for at most six HTTP attempts.
  const reserve=(new TextEncoder().encode(prompt).length+8192)*6;
  let lease:any;
  try { lease=await meshRpc("arbm_mesh_acquire",{p_provider:provider,p_reserve:reserve}); }
  catch { return {result:null,attempts:[{route:provider,status:"shared_control_unavailable",mandatory_cost_usd:0,paid_fallback_used:false}]}; }
  if(lease?.allowed!==true || !lease.lease_id) return {result:null,attempts:[{route:provider,status:lease?.reason || "shared_control_denied",mandatory_cost_usd:0,paid_fallback_used:false}]};
  let out:any;
  try { out=await call(); } catch { out={result:null,attempts:[{route:provider,status:"transport"}]}; }
  const attempts=out.attempts || [];
  const failed=attempts.find((a:any)=>a.status===401||a.status===403||a.status===429||a.status>=500||a.status==="transport");
  const status=failed?.status;
  const health=status===429?"cooling_down":[401,403].includes(status)?"auth_failed":failed?"transient_failure":out.result?"healthy":"transient_failure";
  const retry=status===429?Math.ceil(mistralRetryMs(failed.retry_after)/1000):[401,403].includes(status)?300:health==="healthy"?0:30;
  const network=attempts.filter((a:any)=>typeof a.status==="number"||a.status==="transport");
  const usage=network.every((a:any)=>Number.isFinite(a.usage_tokens)&&a.usage_tokens>=0)?network.reduce((n:number,a:any)=>n+a.usage_tokens,0):null;
  const completed=await meshRpc("arbm_mesh_complete",{p_provider:provider,p_lease:lease.lease_id,p_health:health,p_usage:usage,p_retry_seconds:Math.min(2678400,retry)}).catch(()=>null);
  if(completed?.accepted!==true) return {result:null,attempts:[...attempts,{route:provider,status:"shared_completion_failed",mandatory_cost_usd:0,paid_fallback_used:false}]};
  return {result:out.result,attempts:attempts.map((a:any)=>({...a,mandatory_cost_usd:0,paid_fallback_used:false,latency_ms:Date.now()-started,shared_control:true,quota_kind:"internal_policy_not_account_allowance"}))};
}
Deno.serve(async (req: Request) => {
  if (req.method !== "POST") return respond({ error: "METHOD_NOT_ALLOWED" }, 405);
  try {
    const oidc = await auth(req);
    const body = await req.json().catch(() => ({}));
    const instruction = String(body?.instruction || "").slice(0, 16000);
    const observation = String(body?.observation || "").slice(-16000);
    const step = Math.max(1, Math.min(20, Number(body?.step || 1)));
    if (!instruction) return respond({ error: "INSTRUCTION_REQUIRED" }, 400);

    const prompt = `Solve this Terminal-Bench task by inspecting the sandbox, making the smallest correct changes, and verifying them. Return JSON only. Use exec with exactly one bash command, or finish only after verification succeeded. Never repeat a failed or no-progress command.\nSTEP:${step}\nTASK:\n${instruction}\nRECENT HISTORY:\n${observation || "No commands executed yet."}`;
    const attempts: any[] = [];
    let result: any = null;

    const diagnosticBranch = oidc.ref.startsWith("refs/heads/codex/terminal-capacity-") || oidc.ref.startsWith("refs/heads/codex/free-capacity-");
    if ((Deno.env.get("ZERO_SPEND_MODE") || "HARD") !== "HARD") return respond({ok:false,status:"ZERO_SPEND_HARD_REQUIRED",mandatory_cost_usd:0,paid_fallback_used:false},503);
    const forced = diagnosticBranch && ["groq","google","lightning","mistral","cloudflare"].includes(body?.provider_hint) ? body.provider_hint : "";
    const modelHint = diagnosticBranch ? String(body?.model_hint || "") : "";
    const order = step>=3 ? ["groq","google","lightning","mistral"] : ["lightning","google","groq","mistral"];
    if ((hashText(prompt)+step)%4===3) order.unshift(order.splice(order.indexOf("mistral"),1)[0]);
    const providers=forced?[forced]:[...order,"cloudflare"];
    const deadline=Date.now()+55000;
    for (const provider of providers) {
      if(Date.now()>deadline){attempts.push({route:provider,status:"request_deadline",mandatory_cost_usd:0,paid_fallback_used:false});break;}
      const hint=forced?modelHint:"";
      const invoke=()=>provider==="mistral"?callMistral(prompt,hint):provider==="lightning"?callLightning(prompt,step,hint):provider==="groq"?callGroq(prompt,step,hint):provider==="google"?callGemini(prompt,step,hint):callCloudflare(prompt,hint);
      const response=provider==="cloudflare"?await invoke():await controlled(provider,prompt,invoke);
      attempts.push(...response.attempts);result=response.result;
      if(result)break;
    }
    if (!result) {
      return respond({
        ok: false,
        status: "WAITING_FREE_CAPACITY",
        provider_attempts: attempts,
        mandatory_cost_usd: 0,
        paid_fallback_used: false,
        scoreable: false
      }, 503);
    }

    const action = result.action || {};
    if (!["exec", "finish"].includes(String(action.action))) {
      return respond({ ok: false, status: "INVALID_ACTION", provider_attempts: attempts, mandatory_cost_usd: 0 }, 422);
    }
    if (action.action === "exec" && !String(action.command || "").trim()) {
      return respond({ ok: false, status: "INVALID_ACTION", provider_attempts: attempts, mandatory_cost_usd: 0 }, 422);
    }

    return respond({
      ok: true,
      status: "PASS",
      action: {
        action: String(action.action),
        command: String(action.command || "").slice(0, 6000),
        summary: String(action.summary || "").slice(0, 1000)
      },
      model: result.model,
      provider: result.provider,
      provider_attempts: attempts,
      pipeline: "terminal-agent-v16-shared-free-mesh",
      mandatory_cost_usd: 0,
      paid_fallback_used: false,
      scoreable: false,
      github_run_id: oidc.runId,
      github_sha: oidc.sha
    });
  } catch (error: any) {
    const message = String(error?.message || error);
    const unauthorized = message.startsWith("OIDC_") || message.includes("JWT") || message.includes("signature");
    return respond({
      error: unauthorized ? "OIDC_UNAUTHORIZED" : "INTERNAL_ERROR",
      detail: unauthorized ? message : undefined
    }, unauthorized ? 401 : 500);
  }
});


