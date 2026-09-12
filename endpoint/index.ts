import "jsr:@supabase/functions-js@2.116.0/edge-runtime.d.ts";
import { createRemoteJWKSet, jwtVerify } from "npm:jose@5.10.0";

const ISS = "https://token.actions.githubusercontent.com";
const AUD = "arbm-sist-benchmark";
const REPO = "arbmsistone-lab/arbm-sist-external-exec-proof";
const JWKS = createRemoteJWKSet(new URL(ISS + "/.well-known/jwks"));
const BUILD = "arbm-osworld-elite-pro-v31q-20260912";
const PIPELINE = "arbm-osworld-v31-isolated";
const GROQ_URL = "https://api.groq.com/openai/v1/chat/completions";
const MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions";
const GROQ_MODELS = ["qwen/qwen3.8-27b", "qwen/qwen3.6-27b"];
const GROQ_TEXT_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"];
const MISTRAL_MODELS = ["mistral-small-latest", "ministral-8b-latest", "ministral-3b-latest"];
const COOLDOWN = new Map<string, number>();

const respond = (x: unknown, status = 200) => new Response(JSON.stringify(x), { status, headers: { "content-type": "application/json", "cache-control": "no-store" } });
const scrub = (v: unknown) => String(v || "").replace(/Bearer\s+[^\s\"']+/gi, "Bearer [redacted]").slice(0, 500);
const parseJson = (text: string) => {
  const c = String(text || "").trim().replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/i, "");
  try { return JSON.parse(c); } catch {}
  const a = c.indexOf("{"), b = c.lastIndexOf("}");
  if (a >= 0 && b > a) { try { return JSON.parse(c.slice(a, b + 1)); } catch {} }
  return null;
};
const textField=(value:unknown)=>typeof value==="string"?value:(value==null?"":JSON.stringify(value));
const cooling = (k: string) => (COOLDOWN.get(k) || 0) > Date.now();
const cool = (k: string, seconds = 60) => COOLDOWN.set(k, Date.now() + seconds * 1000);

async function auth(req: Request) {
  const m = /^Bearer\s+(.+)$/i.exec(req.headers.get("authorization") || "");
  if (!m) throw new Error("OIDC_MISSING");
  const { payload } = await jwtVerify(m[1], JWKS, { issuer: ISS, audience: AUD, algorithms: ["RS256"] });
  if (payload.repository !== REPO) throw new Error("OIDC_REPOSITORY");
  const ref = String(payload.ref || "");
  if (!(ref.startsWith("refs/heads/codex/osworld-close-") || ref.startsWith("refs/heads/codex/free-capacity-osworld-v31-providers-"))) throw new Error("OIDC_REF");
  if (!["push", "workflow_dispatch"].includes(String(payload.event_name || ""))) throw new Error("OIDC_EVENT");
  return { runId: String(payload.run_id || ""), sha: String(payload.sha || ""), ref };
}

function splitStatements(value: string) {
  const out: string[] = [];
  let current = "", quote = "", escaped = false, depth = 0;
  for (const ch of String(value || "")) {
    if (escaped) { current += ch; escaped = false; continue; }
    if (quote) {
      current += ch;
      if (ch === "\\") escaped = true;
      else if (ch === quote) quote = "";
      continue;
    }
    if (ch === "'" || ch === "\"") { quote = ch; current += ch; continue; }
    if (ch === "(" || ch === "[" || ch === "{") { depth++; current += ch; continue; }
    if (ch === ")" || ch === "]" || ch === "}") { depth = Math.max(0, depth - 1); current += ch; continue; }
    if ((ch === ";" || ch === "\n") && depth === 0) {
      if (current.trim()) out.push(current.trim());
      current = "";
      continue;
    }
    current += ch;
  }
  if (current.trim()) out.push(current.trim());
  return out;
}

function normalizeCommand(command: string) {
  const clean = String(command || "").trim().replace(/^```(?:python)?\s*/i, "").replace(/\s*```$/i, "");
  return splitStatements(clean).filter(x => !/^import\s+pyautogui\s*$/i.test(x) && !x.startsWith("#")).join("\n");
}


function validate(command: string) {
  if (typeof command !== 'string' || !command.trim() || command.length>5000) return 'EMPTY_OR_TOO_LONG';
  const str=String.raw`(?:'(?:[^'\\\r\n]|\\.)*'|"(?:[^"\\\r\n]|\\.)*")`;
  const atom=String.raw`(?:${str}|-?\d+(?:\.\d+)?|True|False|None)`;
  const list=String.raw`\[\s*(?:${atom}(?:\s*,\s*${atom})*,?)?\s*\]`;
  const arg=String.raw`(?:[a-zA-Z_]\w*\s*=\s*)?(?:${atom}|${list})`;
  const line=new RegExp(String.raw`^pyautogui\.(?:click|doubleClick|rightClick|moveTo|press|hotkey|write|typewrite|scroll|sleep|mouseDown|mouseUp|dragTo|keyDown|keyUp)\s*\(\s*(?:${arg}(?:\s*,\s*${arg})*,?)?\s*\)$`);
  const lines=splitStatements(command);
  return !lines.length||lines.length>8||lines.some(x=>!line.test(x))?'DIRECT_LITERAL_GUI_CALL_REQUIRED':'';
}
function canonicalAction(value: any) {
  if(!value||typeof value!=='object'||Array.isArray(value)) throw new Error('ACTION_OBJECT_REQUIRED');
  let kind=String(value.action||'').trim().toLowerCase(),command=value.command||'';
  if(typeof command!=='string') throw new Error('COMMAND_STRING_REQUIRED');
  if(['execute','plan','click','type'].includes(kind))kind=command.trim()?'exec':'wait';
  if(!['exec','wait','finish'].includes(kind))throw new Error('INVALID_ACTION');
  command=kind==='exec'?normalizeCommand(command):'';
  if(kind==='exec'&&validate(command))throw new Error(validate(command));
  return {...value,action:kind,command};
}
function prompt(body: any) {
  return `You control an Ubuntu desktop by visible GUI only. Return ONE JSON object.
Planner: choose the next unmet subtask, maintain brief factual memory. Executor: one small GUI action, or at most 4 tightly related calls. Verifier: describe what visibly changed after the previous action and what change to expect next. An executed call is NOT proof of progress.
CRITICAL GROUNDING: the screenshot shows the foreground. The accessibility tree includes BACKGROUND windows and desktop labels covered by other windows. Never click a tree coordinate unless the target is visible at that spot in the screenshot. First bring the intended window forward via its visible dock icon or Alt+Tab. To access Desktop files hidden behind a maximized window, use Ctrl+Super+D to show Desktop, then DOUBLE-click the visible file. Use center coordinates (top-left plus half size), never the top-left boundary.
If a click did nothing, do not repeat it: inspect foreground, try keyboard navigation, show Desktop, or use file manager and its location field. Opening a file requires doubleClick or selecting it and pressing Enter. Single click usually only selects. Do not assume unseen content.
Only direct pyautogui calls with literal arguments, one per line. command MUST be a STRING, never an array/object or explanations. No shell, terminal, scripts, filesystem/network APIs, clipboard extraction, hidden state or benchmark internals. Typing a path into a visible GUI file dialog is allowed. Scroll by 3-6 not hundreds. sleep <= 3s.
Required JSON:
{"action":"exec|wait|finish","command":"pyautogui...","plan":"current subtask","summary":"why this action","memory_patch":"durable observed facts and completed subtasks","verification":"visible result of previous action","expected_change":"next visible outcome","confidence":0.9,"checkpoint":{"name":"next subtask milestone","application":"exact expected Ubuntu panel app name","visible_text":"exact text expected to appear after action"}}
checkpoint is a proposed observation predicate, never a claim of completion. Set application and visible_text to the exact expected foreground evidence. The local independent verifier will check the NEXT observation; consult verified_milestones and continue from the last confirmed milestone. Do not reopen a file already confirmed open. Do not switch to an output app before reading the required source facts.
All descriptive fields except checkpoint must be short factual strings, never nested objects. Use exec for GUI work. Plan is internal, never an action. Finish only when ALL requested outputs are saved and verified on screen; confidence>=0.8. Never claim completion from intent.
FOREGROUND APPLICATION: ${body.active_application||"unknown"}. Any different application in the tree is background. A Home desktop label is NOT a dock icon. To reveal Desktop use pyautogui.hotkey('ctrl','win','d'), never click Home through a window.
STEP ${body.step}, NO_PROGRESS ${body.no_progress_count}, RECOVERY ${body.recovery_strategy||'normal'}
TASK: ${String(body.instruction||'').slice(0,7000)}
MEMORY: ${String(body.memory||'').slice(-4500)}
PREVIOUS: ${String(body.previous_command||'').slice(-1500)}
VERIFIER: ${JSON.stringify(body.verifier||{})}
VERIFIED MILESTONES: ${JSON.stringify(body.verified_milestones||[])}
SCREENSHOT: original desktop coordinates ${body.image_geometry?.width||1920}x${body.image_geometry?.height||1080}. The transmitted image is ${body.image_geometry?.transmitted_width||1920}x${body.image_geometry?.transmitted_height||1080}; scale screenshot coordinates to the original desktop or use tree control centers. Screenshot is authoritative for visibility.
ACCESSIBILITY (may include occluded background controls):
${String(body.observation||'').slice(0,9000)}`;
}

async function callGroq(p: string, image: string, body: any, textOnly = false) {
  p=prompt({...body,observation:String(body.observation||"").slice(0,3500),memory:String(body.memory||"").slice(-1800)});
  const route=textOnly?"groq-accessibility-free":"groq-multimodal-free";
  if(textOnly)p=prompt({...body,observation:String(body.observation||"").slice(0,6500),memory:String(body.memory||"").slice(-2000)})+"\nMODALITY: TEXT ONLY. You have NO screenshot. Use foreground accessibility controls only. Prefer keyboard shortcuts. Never invent visual coordinates; if uncertain choose keyboard navigation to bring the needed app forward. Do not claim to see images.";
  const key = String(Deno.env.get("GROQ_API_KEY") || "").trim();
  if (!key) return { result: null, attempts: [{ route, status: "not_configured" }] };
  const attempts: any[] = [];
  for (const model of (textOnly?GROQ_TEXT_MODELS:GROQ_MODELS)) {
    if(Date.now()>body.request_deadline-1000)break;
    if (cooling("g:" + model) || Number(body.route_cooldowns?.[route+":"+model]||0)>Date.now()) { attempts.push({ route, model, status: "cooldown" }); continue; }
    try {
      const content: any = textOnly?p:[{ type: "text", text: p }, { type: "image_url", image_url: { url: image } }];
      const providerBody=JSON.stringify({ model, messages: [{ role: "system", content: "Return one valid JSON object only." }, { role: "user", content }], response_format: { type: "json_object" }, temperature: 0, reasoning_effort: textOnly?"low":"none", max_completion_tokens: textOnly?1600:850 });
      const requestBytes=new TextEncoder().encode(providerBody).length;
      if(requestBytes>420000){attempts.push({route,model,status:"payload_gate",request_bytes:requestBytes});continue;}
      const res = await fetch(GROQ_URL, { method: "POST", headers: { "content-type": "application/json", authorization: `Bearer ${key}` }, body: providerBody, signal: AbortSignal.timeout(Math.max(1000,Math.min(35000,body.request_deadline-Date.now()))) });
      const raw = await res.json().catch(() => ({}));
      let out = res.ok ? parseJson(String(raw?.choices?.[0]?.message?.content || "")) : null;
      let contractError=""; try {if(out)out=canonicalAction(out);}catch(e:any){contractError=String(e.message);out=null;}
      const rpd = res.headers.get("x-ratelimit-limit-requests"), tpm = res.headers.get("x-ratelimit-limit-tokens"), remaining = res.headers.get("x-ratelimit-remaining-requests"), retryAfter = res.headers.get("retry-after");
      const free = rpd === "1000" && tpm === "8000";
      if (res.status === 429 || remaining === "0" || res.status===413) cool("g:" + model, res.status===413?3600:Math.max(60, Number(retryAfter || 0)));
      attempts.push({ route, model, status: res.status, parsed: !!out, contract_error: contractError, request_bytes: requestBytes, prompt_tokens: raw?.usage?.prompt_tokens, completion_tokens: raw?.usage?.completion_tokens, response_text: String(raw?.choices?.[0]?.message?.content||raw?.error?.failed_generation||"").slice(0,6000), free_plan_proven: free, rate_limit_rpd: rpd, rate_limit_tpm: tpm, remaining_requests: remaining, retry_after: retryAfter, error_message: scrub(raw?.error?.message), mandatory_cost_usd: 0, paid_fallback_used: false });
      if (out && free) return { result: { action: out, provider: "groqcloud-free", model, zeroSpendProven: true }, attempts };
      if ([401, 403].includes(res.status)) break;
      if (res.status === 429 || res.status >= 500 || [400, 404, 422].includes(res.status)) continue;
    } catch (e: any) {
      attempts.push({ route, model, status: "transport", error: scrub(e?.message || e), mandatory_cost_usd: 0, paid_fallback_used: false });
      continue;
    }
  }
  return { result: null, attempts };
}

async function callGroqText(p:string,image:string,body:any){return callGroq(p,image,body,true);}

async function callMistral(p: string, image: string, body: any) {
  const key = String(Deno.env.get("MISTRAL_API_KEY") || "").trim();
  const confirmed = String(Deno.env.get("ARBM_MISTRAL_ZERO_SPEND_CONFIRMED") || "") === "1" && String(Deno.env.get("ARBM_MISTRAL_LIVE_PROVEN") || "") === "1";
  if (!key || !confirmed) return { result: null, attempts: [{ route: "mistral-multimodal-free", status: key ? "zero_spend_unconfirmed" : "not_configured", mandatory_cost_usd: 0, paid_fallback_used: false }] };
  const attempts: any[] = [];
  for (const model of MISTRAL_MODELS) {
    if(Date.now()>body.request_deadline-1000)break;
    if (cooling("m:" + model) || Number(body.route_cooldowns?.["mistral-multimodal-free:"+model]||0)>Date.now()) { attempts.push({ route: "mistral-multimodal-free", model, status: "cooldown" }); continue; }
    try {
      const content: any[] = [{ type: "text", text: p }, { type: "image_url", image_url: image }];
      const providerBody=JSON.stringify({ model, messages: [{ role: "system", content: "Return JSON only." }, { role: "user", content }], temperature: 0, max_tokens: 900, response_format: { type: "json_object" } });
      const requestBytes=new TextEncoder().encode(providerBody).length;
      if(requestBytes>420000){attempts.push({route:"mistral-multimodal-free",model,status:"payload_gate",request_bytes:requestBytes});continue;}
      const res = await fetch(MISTRAL_URL, { method: "POST", headers: { "content-type": "application/json", authorization: `Bearer ${key}` }, body: providerBody, signal: AbortSignal.timeout(Math.max(1000,Math.min(35000,body.request_deadline-Date.now()))) });
      const raw = await res.json().catch(() => ({}));
      let out = res.ok ? parseJson(String(raw?.choices?.[0]?.message?.content || "")) : null;
      let contractError=""; try {if(out)out=canonicalAction(out);}catch(e:any){contractError=String(e.message);out=null;}
      const retryAfter = res.headers.get("retry-after");
      if (res.status === 429) cool("m:" + model, Math.max(60, Number(retryAfter || 0)));
      attempts.push({ route: "mistral-multimodal-free", model, status: res.status, parsed: !!out, contract_error: contractError, request_bytes: requestBytes, prompt_tokens: raw?.usage?.prompt_tokens, completion_tokens: raw?.usage?.completion_tokens, response_text: String(raw?.choices?.[0]?.message?.content||raw?.error?.failed_generation||"").slice(0,6000), zero_spend_confirmed: true, retry_after: retryAfter, error_message: scrub(raw?.message || raw?.error?.message), mandatory_cost_usd: 0, paid_fallback_used: false });
      if (out) return { result: { action: out, provider: "mistral-free", model, zeroSpendProven: true }, attempts };
      if ([401, 403].includes(res.status)) break;
      if (res.status === 429 || res.status >= 500 || [400, 404, 422].includes(res.status)) continue;
    } catch (e: any) {
      attempts.push({ route: "mistral-multimodal-free", model, status: "transport", error: scrub(e?.message || e), mandatory_cost_usd: 0, paid_fallback_used: false });
      continue;
    }
  }
  return { result: null, attempts };
}

Deno.serve(async (req: Request) => {
  if (req.method !== "POST") return respond({ error: "METHOD_NOT_ALLOWED" }, 405);
  try {
    const oidc = await auth(req);
    const body = await req.json().catch(() => ({}));
    if (!String(body?.instruction || "").trim()) return respond({ error: "INSTRUCTION_REQUIRED" }, 400);
    if(body.expected_build && body.expected_build!==BUILD)return respond({ok:false,status:"ENDPOINT_INCOMPATIBLE",pipeline:PIPELINE,agent_build:BUILD,mandatory_cost_usd:0,paid_fallback_used:false},409);
    if(new TextEncoder().encode(JSON.stringify(body)).length>420000)return respond({ok:false,status:"PAYLOAD_GATE",pipeline:PIPELINE,agent_build:BUILD,mandatory_cost_usd:0,paid_fallback_used:false},413);
    const image = String(body?.screenshot_data_url || "");
    if (!image) return respond({ ok: false, status: "MULTIMODAL_IMAGE_REQUIRED", pipeline: PIPELINE, agent_build: BUILD, mandatory_cost_usd: 0, paid_fallback_used: false }, 400);
    body.request_deadline=Date.now()+125000;
    const p = prompt(body), hint = String(body?.provider_hint || "");
    const attempts: any[] = [];
    let result: any = null;
    const routes=hint==="text"?[callGroqText,callGroq,callMistral]:hint==="mistral"?[callMistral,callGroq,callGroqText]:[callGroq,callGroqText,callMistral];
    for(const route of routes){const r=await route(p,image,body);attempts.push(...r.attempts);if(r.result){result=r.result;break;}}
    if (!result) return respond({ ok: false, status: "NO_ZERO_SPEND_MULTIMODAL_CAPACITY", pipeline: PIPELINE, agent_build: BUILD, provider_attempts: attempts, mandatory_cost_usd: 0, paid_fallback_used: false, scoreable: false }, 503);
    const a = canonicalAction(result.action || {});
    if (!["exec", "finish", "wait"].includes(String(a.action))) return respond({ ok: false, status: "INVALID_ACTION", pipeline: PIPELINE, agent_build: BUILD, provider_attempts: attempts, mandatory_cost_usd: 0, paid_fallback_used: false }, 422);
    const normalized = a.action === "exec" ? normalizeCommand(String(a.command || "")) : "";
    const reason = a.action === "exec" ? validate(normalized) : "";
    if (reason) return respond({ ok: false, status: "ACTION_REJECTED", reason, rejected_command: scrub(String(a.command || "")), pipeline: PIPELINE, agent_build: BUILD, provider_attempts: attempts, mandatory_cost_usd: 0, paid_fallback_used: false }, 422);
    if (a.action === "finish" && (Number(a.confidence || 0) < 0.72 || !textField(a.verification).trim())) return respond({ ok: false, status: "FINISH_NOT_VERIFIED", pipeline: PIPELINE, agent_build: BUILD, provider_attempts: attempts, mandatory_cost_usd: 0, paid_fallback_used: false }, 422);
    return respond({ ok: true, status: "PASS", pipeline: PIPELINE, agent_build: BUILD, action: { action: String(a.action), command: normalized.slice(0, 5000), summary: textField(a.summary).slice(0, 1400), checkpoint: a.checkpoint && typeof a.checkpoint==="object" ? {name:textField(a.checkpoint.name).slice(0,200),application:textField(a.checkpoint.application).slice(0,100),visible_text:textField(a.checkpoint.visible_text).slice(0,300)} : null, modality: result.model.startsWith("openai/gpt-oss")?"accessibility-text":"screenshot-and-accessibility", phase: String(a.phase || "execute"), plan: textField(a.plan).slice(0, 3500), memory_patch: textField(a.memory_patch).slice(0, 3500), verification: textField(a.verification).slice(0, 2500), expected_change: textField(a.expected_change).slice(0,1000), confidence: Math.max(0, Math.min(1, Number(a.confidence || 0))) }, provider: result.provider, model: result.model, provider_attempts: attempts, mandatory_cost_usd: 0, paid_fallback_used: false, scoreable: false, github_run_id: oidc.runId, github_sha: oidc.sha });
  } catch (e: any) {
    const m = String(e?.message || e), unauthorized = m.startsWith("OIDC_") || m.includes("JWT") || m.includes("signature");
    return respond({ error: unauthorized ? "OIDC_UNAUTHORIZED" : "INTERNAL_ERROR", detail: unauthorized ? m : scrub(m), pipeline: PIPELINE, agent_build: BUILD, mandatory_cost_usd: 0, paid_fallback_used: false }, unauthorized ? 401 : 500);
  }
});

