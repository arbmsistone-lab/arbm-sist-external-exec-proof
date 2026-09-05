import assert from 'node:assert/strict';
import { evaluateCodexParity, REQUIRED_DIMENSIONS } from './codex-parity-gate.mjs';

const hashes = ['a'.repeat(64)];
const base = {
  reference: { product: 'OpenAI Codex', capturedAt: '2026-09-04T00:00:00Z', validUntil: '2026-10-04T23:59:59Z', publicSources: ['official'] },
  qualityPolicy: { mode: 'CODEX_HARD_FLOOR', sameTaskContract: true, confidenceLevel: 0.95, nonInferiorityMarginPp: 2, noQualityDowngradeForCost: true },
  costPolicy: { mode: 'ZERO_SPEND_HARD', zeroSpendMode: 'HARD', paidEscalationAllowed: false, benchmarkCostTracked: true, maxMandatoryAiCostBRLPerActiveUserMonth: 0, arbmProviderCostPerResolvedTaskBRL: 0 },
  p8Complete: true,
  p9IndependentAudit: true,
  failedRunsDisclosed: true,
  rawArtifactsHashed: true,
  noHiddenEvaluatorFeedback: true,
  continuousParityWatch: true,
  dimensions: REQUIRED_DIMENSIONS.map((id) => ({ id, arbm: 0.80, codex: 0.80, samples: 30, ciLowerDifferencePp: -1.0, artifactSha256: hashes })),
};

const now = new Date('2026-09-10T00:00:00Z');
assert.equal(evaluateCodexParity(base, now).pass, true);

const paid = structuredClone(base);
paid.costPolicy.paidEscalationAllowed = true;
assert.ok(evaluateCodexParity(paid, now).reasons.includes('PAID_ESCALATION_FORBIDDEN'));

const nonzero = structuredClone(base);
nonzero.costPolicy.arbmProviderCostPerResolvedTaskBRL = 0.01;
assert.ok(evaluateCodexParity(nonzero, now).reasons.includes('RESOLVED_TASK_PROVIDER_COST_NOT_ZERO'));

const weak = structuredClone(base);
weak.dimensions[0].ciLowerDifferencePp = -2.1;
assert.ok(evaluateCodexParity(weak, now).reasons.some((r) => r.startsWith('NON_INFERIORITY_NOT_PROVEN:')));

const stale = structuredClone(base);
assert.ok(evaluateCodexParity(stale, new Date('2026-10-05T00:00:00Z')).reasons.includes('REFERENCE_EXPIRED'));

console.log('codex parity gate v2 tests: PASS');