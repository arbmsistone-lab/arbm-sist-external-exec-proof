import assert from 'node:assert/strict';
import { evaluateCodexParity, REQUIRED_DIMENSIONS } from './codex-parity-gate.mjs';

const hash = 'a'.repeat(64);
const good = () => ({
  reference: {
    product: 'OpenAI Codex',
    capturedAt: '2026-09-04T00:00:00Z',
    publicSources: ['https://openai.com/index/running-codex-safely/'],
  },
  zeroSpendHard: true,
  p8Complete: true,
  p9IndependentAudit: true,
  p9Audit: { auditor: 'independent-auditor', completedAt: '2026-09-04T01:00:00Z', sourceCommit: hash, artifactSha256: [hash] },
  failedRunsDisclosed: true,
  rawArtifactsHashed: true,
  rawArtifactSha256: [hash],
  noHiddenEvaluatorFeedback: true,
  dimensions: REQUIRED_DIMENSIONS.map((id) => ({
    id, arbm: 0.8, codex: 0.8, samples: 3, artifactSha256: [hash],
  })),
});

const has = (r, reason) => r.reasons.some((x) => x === reason);
let cases = 0;
const check = (fn) => { fn(); cases += 1; };

check(() => assert.equal(evaluateCodexParity(good()).pass, true));
check(() => { const e=good(); e.dimensions[0].arbm=.79; assert(has(evaluateCodexParity(e),'BELOW_CODEX:task_correctness')); });
check(() => { const e=good(); e.p8Complete=false; assert(has(evaluateCodexParity(e),'P8_INCOMPLETE')); });
check(() => { const e=good(); e.p9IndependentAudit=false; assert(has(evaluateCodexParity(e),'P9_INDEPENDENT_AUDIT_MISSING')); });
check(() => { const e=good(); e.zeroSpendHard=false; assert(has(evaluateCodexParity(e),'ZERO_SPEND_POLICY_NOT_PROVEN')); });
check(() => { const e=good(); e.dimensions[0].samples=2; assert(has(evaluateCodexParity(e),'INSUFFICIENT_SAMPLES:task_correctness')); });
check(() => { const e=good(); e.dimensions=e.dimensions.slice(1); assert(has(evaluateCodexParity(e),'DIMENSION_MISSING:task_correctness')); });
check(() => { const e=good(); e.rawArtifactsHashed=false; assert(has(evaluateCodexParity(e),'RAW_ARTIFACT_HASHES_MISSING')); });
check(() => { const e=good(); e.noHiddenEvaluatorFeedback=false; assert(has(evaluateCodexParity(e),'HIDDEN_EVALUATOR_FIREWALL_NOT_PROVEN')); });
check(() => { const e=good(); e.failedRunsDisclosed=false; assert(has(evaluateCodexParity(e),'FAILED_RUNS_NOT_DISCLOSED')); });

check(() => { const e=good(); e.p9Audit.auditor=''; assert(has(evaluateCodexParity(e),'P9_AUDITOR_IDENTITY_MISSING')); });
check(() => { const e=good(); e.p9Audit.completedAt='not-a-date'; assert(has(evaluateCodexParity(e),'P9_AUDIT_DATE_MISSING')); });
check(() => { const e=good(); e.p9Audit.sourceCommit='bad'; assert(has(evaluateCodexParity(e),'P9_AUDIT_COMMIT_INVALID')); });
check(() => { const e=good(); e.p9Audit.artifactSha256=['bad']; assert(has(evaluateCodexParity(e),'P9_AUDIT_HASHES_INVALID')); });
check(() => { const e=good(); e.rawArtifactSha256=[]; assert(has(evaluateCodexParity(e),'RAW_ARTIFACT_HASH_LIST_INVALID')); });

console.log(JSON.stringify({suite:'CODEX-PARITY-GATE-V1',pass:cases,total:cases,score:100}));
