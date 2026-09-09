import OpenAI from "openai";
import { createRemoteJWKSet, jwtVerify } from "jose";

const ISSUER = "https://token.actions.githubusercontent.com";
const AUDIENCE = "arbm-sist-benchmark";
const REPOSITORY = "arbmsistone-lab/arbm-sist-external-exec-proof";
const MODEL = "meta-llama/llama-3.1-8b-instruct";
const JWKS = createRemoteJWKSet(new URL(`${ISSUER}/.well-known/jwks`));

async function authorize(req: Request) {
  const auth = req.headers.get("authorization") || "";
  if (!auth.startsWith("Bearer ")) throw new Error("missing_bearer");
  const token = auth.slice(7);
  const { payload } = await jwtVerify(token, JWKS, { issuer: ISSUER, audience: AUDIENCE });
  if (payload.repository !== REPOSITORY) throw new Error("repository_denied");
  const ref = String(payload.ref || "");
  if (!ref.startsWith("refs/heads/codex/free-capacity-")) throw new Error("ref_denied");
  const event = String(payload.event_name || "");
  if (!new Set(["push", "workflow_dispatch"]).has(event)) throw new Error("event_denied");
  return payload;
}
export default async (req: Request) => {
  if (req.method !== "GET") return Response.json({ok:false,error:"method_not_allowed"},{status:405});
  try { await authorize(req); }
  catch { return Response.json({ok:false,error:"unauthorized"},{status:401}); }
  try {
    const client = new OpenAI();
    const r = await client.chat.completions.create({
      model: MODEL,
      messages: [{role:"user",content:"Reply only ARBM_NETLIFY_PASS"}],
      max_tokens: 16,
      temperature: 0
    });
    const text = r.choices?.[0]?.message?.content || "";
    const ok = text.includes("ARBM_NETLIFY_PASS");
    return Response.json({ok,requested_model:MODEL,model:r.model,usage:r.usage||null,mandatory_cost_usd:0,paid_fallback_used:false},{status:ok?200:502});
  } catch (e:any) {
    return Response.json({ok:false,error:String(e?.name||"gateway_error"),mandatory_cost_usd:0,paid_fallback_used:false},{status:503});
  }
};