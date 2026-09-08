import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createRemoteJWKSet, jwtVerify } from "npm:jose@5.10.0";

const ISS = "https://token.actions.githubusercontent.com";
const AUD = "arbm-sist-benchmark";
const REPO = "arbmsistone-lab/arbm-sist-external-exec-proof";
const JWKS = createRemoteJWKSet(new URL(ISS + "/.well-known/jwks"));
const GEMINI_MODELS = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash", "gemini-2.5-flash-lite"];
const GROQ_MODELS = ["qwen/qwen3.8-27b", "qwen/qwen3.6-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b"];
const GROQ_URL = "https://api.groq.com/openai/v1/chat/completions";

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
  try { return JSON.parse(clean); } catch { return null; }
}

function extractGemini(raw: any) {
  return (raw?.candidates?.[0]?.content?.parts || []).map((p: any) => p?.text || "").join("");
}
async function callGemini(prompt: string, modelHint = "") {
  const key = String(Deno.env.get("GEMINI_API_KEY") || "").trim();
  if (!key) return { result: null, attempts: [{ route: "google", status: "not_configured" }] };
  const attempts: any[] = [];
  const models = modelHint && GEMINI_MODELS.includes(modelHint) ? [modelHint] : GEMINI_MODELS;
  for (const model of models) {
    try {
      const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`, {
        method: "POST",
        headers: { "content-type": "application/json", "x-goog-api-key": key },
        body: JSON.stringify({
          contents: [{ parts: [{ text: prompt }] }],
          generationConfig: {
            maxOutputTokens: 320,
            responseMimeType: "application/json",
            responseJsonSchema: schema
          }
        }),
        signal: AbortSignal.timeout(20000)
      });
      const raw = await res.json().catch(() => ({}));
      const action = res.ok ? parseJson(extractGemini(raw)) : null;
      attempts.push({ route: "google", model, status: res.status, parsed: !!action });
      if (action) return { result: { action, model, provider: "google-gemini" }, attempts };
    } catch (error: any) {
      attempts.push({ route: "google", model, status: "transport", error: String(error?.name || "Error") });
    }
  }
  return { result: null, attempts };
}
async function callGroq(prompt: string) {
  const key = String(Deno.env.get("GROQ_API_KEY") || "").trim();
  if (!key) return { result: null, attempts: [{ route: "groq", status: "not_configured" }] };
  const attempts: any[] = [];
  const system = "You are ARBM SIST in a Terminal-Bench sandbox. No tools are available. Never emit tool calls. Output exactly one JSON object with keys action, command, summary. action must be exec or finish.";
  for (const model of GROQ_MODELS) {
    try {
      const res = await fetch(GROQ_URL, {
        method: "POST",
        headers: { "content-type": "application/json", authorization: `Bearer ${key}` },
        body: JSON.stringify({ model, messages: [{ role: "system", content: system }, { role: "user", content: prompt }], response_format: { type: "json_object" }, reasoning_effort: "low", max_completion_tokens: 320 }),
        signal: AbortSignal.timeout(30000)
      });
      const raw = await res.json().catch(() => ({}));
      const action = res.ok ? parseJson(String(raw?.choices?.[0]?.message?.content || "")) : null;
      const rpd = res.headers.get("x-ratelimit-limit-requests"), tpm = res.headers.get("x-ratelimit-limit-tokens");
      const retryAfter = res.headers.get("retry-after") || res.headers.get("x-ratelimit-reset-tokens");
      const freePlanProven = rpd === "1000" && tpm === "8000";
      attempts.push({ route: "groq-json-object", model, status: res.status, parsed: !!action, free_plan_proven: freePlanProven, rate_limit_rpd: rpd, rate_limit_tpm: tpm, retry_after: retryAfter, error_message: String(raw?.error?.message || "").slice(0, 300) });
      if (action && freePlanProven) return { result: { action, model, provider: "groqcloud-free" }, attempts };
      if (res.status === 401 || res.status === 403) break;
      continue;
    } catch (error: any) {
      attempts.push({ route: "groq-json-object", model, status: "transport", error: String(error?.name || "Error") });
    }
  }
  return { result: null, attempts };
}
async function callCloudflare(prompt: string) {
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
        schema
      }),
      signal: AbortSignal.timeout(25000)
    });
    const raw = await res.text();
    if (!res.ok) return { result: null, attempts: [{ route: "cloudflare", status: res.status }] };
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
    const forceGroq = body?.provider_hint === "groq" && diagnosticBranch;
    const forceGoogle = body?.provider_hint === "google" && diagnosticBranch;
    const modelHint = diagnosticBranch ? String(body?.model_hint || "") : "";
    if (!forceGroq) {
      const google = await callGemini(prompt, modelHint);
      attempts.push(...google.attempts);
      result = google.result;
    }

    if (!result && !forceGoogle) {
      const groq = await callGroq(prompt);
      attempts.push(...groq.attempts);
      result = groq.result;
    }

    if (!result && !forceGroq && !forceGoogle) {
      const cloudflare = await callCloudflare(prompt);
      attempts.push(...cloudflare.attempts);
      result = cloudflare.result;
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
      pipeline: "terminal-agent-v7-expanded-free-capacity-mesh",
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


