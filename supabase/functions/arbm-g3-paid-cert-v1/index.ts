import { createRemoteJWKSet, jwtVerify } from "npm:jose@5.10.0";

const ISS = "https://token.actions.githubusercontent.com";
const AUD = "arbm-sist-benchmark-paid";
const REPO = "arbmsistone-lab/arbm-sist-external-exec-proof";
const MODEL = "gemini-3.5-flash";
const JWKS = createRemoteJWKSet(new URL(ISS + "/.well-known/jwks"));

const out = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", "cache-control": "no-store" },
  });

async function auth(req: Request) {
  const match = /^Bearer\s+(.+)$/i.exec(req.headers.get("authorization") || "");
  if (!match) throw new Error("OIDC_MISSING");
  const { payload } = await jwtVerify(match[1], JWKS, {
    issuer: ISS,
    audience: AUD,
    algorithms: ["RS256"],
  });
  if (payload.repository !== REPO || !String(payload.ref || "").startsWith("refs/heads/g3/paid-cert-lane-")) {
    throw new Error("OIDC_SCOPE");
  }
  return payload;
}
function mapMessages(messages: any[]) {
  let system = "";
  const contents: any[] = [];
  for (const message of messages || []) {
    const parts: any[] = [];
    const raw = Array.isArray(message?.content) ? message.content : [{ type: "text", text: String(message?.content || "") }];
    for (const part of raw) {
      if (part?.type === "text" && part.text) {
        if (message.role === "system") system += (system ? "\n" : "") + part.text;
        else parts.push({ text: part.text });
      } else if (part?.type === "image_url") {
        const url = String(part?.image_url?.url || "");
        const match = /^data:([^;]+);base64,(.+)$/.exec(url);
        if (match) parts.push({ inline_data: { mime_type: match[1], data: match[2] } });
      }
    }
    if (parts.length) contents.push({ role: message.role === "assistant" ? "model" : "user", parts });
  }
  return { system, contents };
}

Deno.serve(async (req: Request) => {
  if (req.method !== "POST") return out({ status: "METHOD_NOT_ALLOWED" }, 405);
  try {
    await auth(req);
    const key = String(Deno.env.get("GEMINI_G3_PAID_CERT_KEY") || "").trim();
    if (!key) return out({ status: "PAID_CERT_KEY_NOT_CONFIGURED", paid_lane: true }, 503);
    const body = await req.json().catch(() => ({}));
    let system = "";
    let contents: any[] = [];
    if (Array.isArray(body?.messages)) ({ system, contents } = mapMessages(body.messages));
    else {
      const image = String(body?.image_base64 || "");
      contents = [{ role: "user", parts: [
        { text: String(body?.prompt || "Reply exactly VISION_OK if the supplied image is visible.") },
        ...(image ? [{ inline_data: { mime_type: "image/png", data: image } }] : []),
      ] }];
    }
    if (!contents.length) return out({ status: "INPUT_REQUIRED", paid_lane: true }, 400);
    const requestBody: any = {
      contents,
      generationConfig: {
        temperature: Number(body?.temperature ?? 0),
        maxOutputTokens: Math.min(4096, Math.max(16, Number(body?.max_tokens || 512))),
      },
    };
    if (system) requestBody.systemInstruction = { parts: [{ text: system }] };
    const started = Date.now();
    const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent`, {
      method: "POST",
      headers: { "content-type": "application/json", "x-goog-api-key": key },
      body: JSON.stringify(requestBody),
      signal: AbortSignal.timeout(120000),
    });
    const raw = await response.json().catch(() => ({}));
    const text = (raw?.candidates?.[0]?.content?.parts || []).map((p: any) => p?.text || "").join("").trim();
    const usage = raw?.usageMetadata || {};
    const evidence = {
      requested_model: MODEL,
      resolved_model: raw?.modelVersion || MODEL,
      provider: "google-gemini-developer-api",
      paid_lane: true,
      billing_mode: "PAID_CERTIFICATION_LANE",
      prompt_tokens: usage.promptTokenCount ?? null,
      output_tokens: usage.candidatesTokenCount ?? null,
      total_tokens: usage.totalTokenCount ?? null,
      latency_ms: Date.now() - started,
      secret_values_present: false,
    };
    if (!response.ok || !text) {
      return out({ status: "FAIL", http: response.status, error_code: raw?.error?.status || null, ...evidence }, response.status || 502);
    }
    if (Array.isArray(body?.messages)) {
      return out({ id: crypto.randomUUID(), object: "chat.completion", created: Math.floor(Date.now() / 1000), model: MODEL,
        choices: [{ index: 0, message: { role: "assistant", content: text }, finish_reason: "stop" }], usage: {
          prompt_tokens: evidence.prompt_tokens, completion_tokens: evidence.output_tokens, total_tokens: evidence.total_tokens }, ...evidence });
    }
    return out({
      status: "PASS",
      http: 200,
      image_input: true,
      text_input: true,
      multimodal_response: true,
      parsed_response: true,
      ...evidence,
    });
  } catch (error: any) {
    return out({
      status: "FAIL",
      error: String(error?.message || error).slice(0, 120),
      paid_lane: true,
      billing_mode: "PAID_CERTIFICATION_LANE",
      secret_values_present: false,
    }, 401);
  }
});
