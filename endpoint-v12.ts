import "jsr:@supabase/functions-js@2.116.0/edge-runtime.d.ts";
import { createRemoteJWKSet, jwtVerify } from "npm:jose@5.10.0";

const ISS = "https://token.actions.githubusercontent.com";
const AUD = "arbm-sist-benchmark";
const REPO = "arbmsistone-lab/arbm-sist-external-exec-proof";
const JWKS = createRemoteJWKSet(new URL(ISS + "/.well-known/jwks"));
const BUILD = "arbm-osworld-v31k-isolated-20260911";
const PIPELINE = "arbm-osworld-v31-isolated";
const GROQ_URL = "https://api.groq.com/openai/v1/chat/completions";
const MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions";
const GROQ_MODELS = ["qwen/qwen3.8-27b", "qwen/qwen3.6-27b"];
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
  const v = String(command || "").trim();
  if (!v || v.length > 5000) return "EMPTY_OR_TOO_LONG";
  if (/\b(?:subprocess|requests|urllib|socket|pathlib|shutil|powershell|bash|cmd\.exe|os\.|open\s*\(|eval\s*\(|exec\s*\(|__import__)\b/i.test(v)) return "NON_GUI_CAPABILITY";
  const lines = splitStatements(v).filter(Boolean);
  const ok = /^pyautogui\.(?:click|doubleClick|rightClick|moveTo|press|hotkey|write|typewrite|scroll|sleep|mouseDown|mouseUp|dragTo)\s*\(/;
  if (!lines.length || lines.some(x => !ok.test(x))) return "NON_PYAUTOGUI_ACTION";
  return "";
}

function prompt(body: any) {
  const step = Math.max(1, Math.min(500, Number(body?.step || 1)));
  const executed = Math.max(0, Math.min(500, Number(body?.executed_count || 0)));
  const np = Math.max(0, Math.min(20, Number(body?.no_progress_count || 0)));
  const phase = String(body?.phase || ((step % 8 === 1 || np >= 2) ? "plan" : "execute"));
  const task = String(body?.instruction || "").slice(0, 18000);
  const obs = String(body?.observation || "").slice(0, 42000);
  const memory = String(body?.memory || "").slice(-18000);
  const prev = String(body?.previous_command || "").slice(-5000);
  const visual = String(body?.visual_context || "").slice(0, 4000);
  return `You are ARBM OSWorld v31k, a long-horizon GUI agent for official OSWorld V2. Use only visible GUI via PyAutoGUI; never shell, terminal, filesystem, network, clipboard, subprocess, hidden state, accessibility APIs or benchmark internals.\nArchitecture: planner -> executor -> verifier. Current phase=${phase}. Maintain durable facts/subtasks in memory_patch. Re-plan after no progress or every few actions. Use screenshot plus accessibility structure together.\nFor exec, command MUST contain only direct pyautogui.* calls. Use one direct pyautogui call per line; no imports, variables, loops, helpers, markdown fences or prose.\nFinish only when visible evidence supports every required subtask. For finish, command must be empty and verification must cite visible evidence. Return JSON only with action,command,summary,phase,plan,memory_patch,verification,confidence.\nSTEP:${step}/500\nEXECUTED:${executed}\nNO_PROGRESS:${np}\nTASK:\n${task}\nPERSISTENT_MEMORY:\n${memory || "none"}\nPREVIOUS_COMMAND:\n${prev || "none"}\nVISUAL_CONTEXT:\n${visual || "screenshot attached"}\nACCESSIBILITY_STRUCTURE:\n${obs}`;
}

async function callGroq(p: string, image: string) {
  const key = String(Deno.env.get("GROQ_API_KEY") || "").trim();
  if (!key) return { result: null, attempts: [{ route: "groq-multimodal-free", status: "not_configured" }] };
  const attempts: any[] = [];
  for (const model of GROQ_MODELS) {
    if (cooling("g:" + model)) { attempts.push({ route: "groq-multimodal-free", model, status: "cooldown" }); continue; }
    try {
      const content: any[] = [{ type: "text", text: p }, { type: "image_url", image_url: { url: image } }];
      const res = await fetch(GROQ_URL, { method: "POST", headers: { "content-type": "application/json", authorization: `Bearer ${key}` }, body: JSON.stringify({ model, messages: [{ role: "system", content: "Return one valid JSON object only." }, { role: "user", content }], response_format: { type: "json_object" }, temperature: 0, max_completion_tokens: 900 }), signal: AbortSignal.timeout(35000) });
      const raw = await res.json().catch(() => ({}));
      const out = res.ok ? parseJson(String(raw?.choices?.[0]?.message?.content || "")) : null;
      const rpd = res.headers.get("x-ratelimit-limit-requests"), tpm = res.headers.get("x-ratelimit-limit-tokens"), remaining = res.headers.get("x-ratelimit-remaining-requests"), retryAfter = res.headers.get("retry-after");
      const free = rpd === "1000" && tpm === "8000";
      if (res.status === 429 || remaining === "0") cool("g:" + model, Math.max(60, Number(retryAfter || 0)));
      attempts.push({ route: "groq-multimodal-free", model, status: res.status, parsed: !!out, free_plan_proven: free, rate_limit_rpd: rpd, rate_limit_tpm: tpm, remaining_requests: remaining, retry_after: retryAfter, error_message: scrub(raw?.error?.message), mandatory_cost_usd: 0, paid_fallback_used: false });
      if (out && free) return { result: { action: out, provider: "groqcloud-free", model, zeroSpendProven: true }, attempts };
      if ([401, 403].includes(res.status)) break;
      if (res.status === 429 || res.status >= 500 || [400, 404, 422].includes(res.status)) continue;
    } catch (e: any) {
      attempts.push({ route: "groq-multimodal-free", model, status: "transport", error: scrub(e?.message || e), mandatory_cost_usd: 0, paid_fallback_used: false });
      continue;
    }
  }
  return { result: null, attempts };
}

async function callMistral(p: string, image: string) {
  const key = String(Deno.env.get("MISTRAL_API_KEY") || "").trim();
  const confirmed = String(Deno.env.get("ARBM_MISTRAL_ZERO_SPEND_CONFIRMED") || "") === "1" && String(Deno.env.get("ARBM_MISTRAL_LIVE_PROVEN") || "") === "1";
  if (!key || !confirmed) return { result: null, attempts: [{ route: "mistral-multimodal-free", status: key ? "zero_spend_unconfirmed" : "not_configured", mandatory_cost_usd: 0, paid_fallback_used: false }] };
  const attempts: any[] = [];
  for (const model of MISTRAL_MODELS) {
    if (cooling("m:" + model)) { attempts.push({ route: "mistral-multimodal-free", model, status: "cooldown" }); continue; }
    try {
      const content: any[] = [{ type: "text", text: p }, { type: "image_url", image_url: image }];
      const res = await fetch(MISTRAL_URL, { method: "POST", headers: { "content-type": "application/json", authorization: `Bearer ${key}` }, body: JSON.stringify({ model, messages: [{ role: "system", content: "Return JSON only." }, { role: "user", content }], temperature: 0, max_tokens: 900, response_format: { type: "json_object" } }), signal: AbortSignal.timeout(35000) });
      const raw = await res.json().catch(() => ({}));
      const out = res.ok ? parseJson(String(raw?.choices?.[0]?.message?.content || "")) : null;
      const retryAfter = res.headers.get("retry-after");
      if (res.status === 429) cool("m:" + model, Math.max(60, Number(retryAfter || 0)));
      attempts.push({ route: "mistral-multimodal-free", model, status: res.status, parsed: !!out, zero_spend_confirmed: true, retry_after: retryAfter, error_message: scrub(raw?.message || raw?.error?.message), mandatory_cost_usd: 0, paid_fallback_used: false });
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
    const image = String(body?.screenshot_data_url || "").slice(0, 27_000_000);
    if (!image) return respond({ ok: false, status: "MULTIMODAL_IMAGE_REQUIRED", pipeline: PIPELINE, agent_build: BUILD, mandatory_cost_usd: 0, paid_fallback_used: false }, 400);
    const p = prompt(body), hint = String(body?.provider_hint || "");
    const attempts: any[] = [];
    let result: any = null;
    if (hint !== "mistral") { const g = await callGroq(p, image); attempts.push(...g.attempts); result = g.result; }
    if (!result && hint !== "groq") { const m = await callMistral(p, image); attempts.push(...m.attempts); result = m.result; }
    if (!result) return respond({ ok: false, status: "NO_ZERO_SPEND_MULTIMODAL_CAPACITY", pipeline: PIPELINE, agent_build: BUILD, provider_attempts: attempts, mandatory_cost_usd: 0, paid_fallback_used: false, scoreable: false }, 503);
    const a = result.action || {};
    if (!["exec", "finish", "wait"].includes(String(a.action))) return respond({ ok: false, status: "INVALID_ACTION", pipeline: PIPELINE, agent_build: BUILD, provider_attempts: attempts, mandatory_cost_usd: 0, paid_fallback_used: false }, 422);
    const normalized = a.action === "exec" ? normalizeCommand(String(a.command || "")) : "";
    const reason = a.action === "exec" ? validate(normalized) : "";
    if (reason) return respond({ ok: false, status: "ACTION_REJECTED", reason, rejected_command: scrub(String(a.command || "")), pipeline: PIPELINE, agent_build: BUILD, provider_attempts: attempts, mandatory_cost_usd: 0, paid_fallback_used: false }, 422);
    if (a.action === "finish" && (Number(a.confidence || 0) < 0.72 || !String(a.verification || "").trim())) return respond({ ok: false, status: "FINISH_NOT_VERIFIED", pipeline: PIPELINE, agent_build: BUILD, provider_attempts: attempts, mandatory_cost_usd: 0, paid_fallback_used: false }, 422);
    return respond({ ok: true, status: "PASS", pipeline: PIPELINE, agent_build: BUILD, action: { action: String(a.action), command: normalized.slice(0, 5000), summary: String(a.summary || "").slice(0, 1400), phase: String(a.phase || "execute"), plan: String(a.plan || "").slice(0, 3500), memory_patch: String(a.memory_patch || "").slice(0, 3500), verification: String(a.verification || "").slice(0, 2500), confidence: Math.max(0, Math.min(1, Number(a.confidence || 0))) }, provider: result.provider, model: result.model, provider_attempts: attempts, mandatory_cost_usd: 0, paid_fallback_used: false, scoreable: false, github_run_id: oidc.runId, github_sha: oidc.sha });
  } catch (e: any) {
    const m = String(e?.message || e), unauthorized = m.startsWith("OIDC_") || m.includes("JWT") || m.includes("signature");
    return respond({ error: unauthorized ? "OIDC_UNAUTHORIZED" : "INTERNAL_ERROR", detail: unauthorized ? m : scrub(m), pipeline: PIPELINE, agent_build: BUILD, mandatory_cost_usd: 0, paid_fallback_used: false }, unauthorized ? 401 : 500);
  }
});

