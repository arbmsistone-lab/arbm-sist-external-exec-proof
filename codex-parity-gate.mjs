import fs from 'node:fs';
import { pathToFileURL } from 'node:url';

export const REQUIRED_DIMENSIONS = [
  'task_correctness',
  'repository_understanding',
  'multi_file_change_quality',
  'tool_terminal_execution',
  'failure_recovery',
  'long_horizon_completion',
  'regression_avoidance',
  'sandbox_approval_network_controls',
  'auditability_reproducibility',
  'human_effort',
];

const finiteScore = (x) => Number.isFinite(Number(x)) && Number(x) >= 0 && Number(x) <= 1;
const finiteNumber = (x) => Number.isFinite(Number(x));
const isoDate = (x) => typeof x === 'string' && !Number.isNaN(Date.parse(x));

export function evaluateCodexParity(evidence, now = new Date()) {
  const reasons = [];
  const e = evidence && typeof evidence === 'object' ? evidence : {};
  const ref = e.reference && typeof e.reference === 'object' ? e.reference : {};
  const quality = e.qualityPolicy && typeof e.qualityPolicy === 'object' ? e.qualityPolicy : {};
  const cost = e.costPolicy && typeof e.costPolicy === 'object' ? e.costPolicy : {};

  if (ref.product !== 'OpenAI Codex') reasons.push('REFERENCE_PRODUCT_INVALID');
  if (!isoDate(ref.capturedAt)) reasons.push('REFERENCE_DATE_MISSING');
  if (!isoDate(ref.validUntil)) reasons.push('REFERENCE_VALID_UNTIL_MISSING');
  if (isoDate(ref.validUntil) && now.getTime() > Date.parse(ref.validUntil)) reasons.push('REFERENCE_EXPIRED');
  if (!Array.isArray(ref.publicSources) || ref.publicSources.length < 1) reasons.push('REFERENCE_SOURCES_MISSING');
  if (quality.mode !== 'CODEX_HARD_FLOOR') reasons.push('QUALITY_FLOOR_POLICY_INVALID');
  if (quality.sameTaskContract !== true) reasons.push('SAME_TASK_CONTRACT_NOT_PROVEN');
  if (!finiteNumber(quality.confidenceLevel) || Number(quality.confidenceLevel) < 0.95) reasons.push('CONFIDENCE_BELOW_95');
  if (!finiteNumber(quality.nonInferiorityMarginPp) || Number(quality.nonInferiorityMarginPp) > 2 || Number(quality.nonInferiorityMarginPp) < 0) reasons.push('NON_INFERIORITY_MARGIN_INVALID');
  if (quality.noQualityDowngradeForCost !== true) reasons.push('QUALITY_DOWNGRADE_FOR_COST_NOT_BLOCKED');
  if (e.p8Complete !== true) reasons.push('P8_INCOMPLETE');
  if (e.p9IndependentAudit !== true) reasons.push('P9_INDEPENDENT_AUDIT_MISSING');
  if (e.failedRunsDisclosed !== true) reasons.push('FAILED_RUNS_NOT_DISCLOSED');
  if (e.rawArtifactsHashed !== true) reasons.push('RAW_ARTIFACT_HASHES_MISSING');
  if (e.noHiddenEvaluatorFeedback !== true) reasons.push('HIDDEN_EVALUATOR_FIREWALL_NOT_PROVEN');
  if (e.continuousParityWatch !== true) reasons.push('CONTINUOUS_PARITY_WATCH_MISSING');

  if (cost.mode !== 'ZERO_SPEND_HARD') reasons.push('COST_POLICY_INVALID');
  if (cost.zeroSpendMode !== 'HARD') reasons.push('ZERO_SPEND_MODE_INVALID');
  if (cost.paidEscalationAllowed !== false) reasons.push('PAID_ESCALATION_FORBIDDEN');
  if (cost.benchmarkCostTracked !== true) reasons.push('BENCHMARK_COST_NOT_TRACKED');
  if (!finiteNumber(cost.maxMandatoryAiCostBRLPerActiveUserMonth) || Number(cost.maxMandatoryAiCostBRLPerActiveUserMonth) !== 0) reasons.push('MANDATORY_AI_COST_NOT_ZERO');
  if (!finiteNumber(cost.arbmProviderCostPerResolvedTaskBRL) || Number(cost.arbmProviderCostPerResolvedTaskBRL) !== 0) reasons.push('RESOLVED_TASK_PROVIDER_COST_NOT_ZERO');

  if (!Array.isArray(e.dimensions)) reasons.push('DIMENSIONS_MISSING');
  const byId = new Map((Array.isArray(e.dimensions) ? e.dimensions : []).map((d) => [d?.id, d]));
  const margin = finiteNumber(quality.nonInferiorityMarginPp) ? Number(quality.nonInferiorityMarginPp) : 2;
  for (const id of REQUIRED_DIMENSIONS) {
    const d = byId.get(id);
    if (!d) { reasons.push(`DIMENSION_MISSING:${id}`); continue; }
    if (!finiteScore(d.arbm)) reasons.push(`ARBM_SCORE_INVALID:${id}`);
    if (!finiteScore(d.codex)) reasons.push(`CODEX_SCORE_INVALID:${id}`);
    if (!Number.isInteger(d.samples) || d.samples < 30) reasons.push(`INSUFFICIENT_SAMPLES:${id}`);
    if (!Array.isArray(d.artifactSha256) || d.artifactSha256.length < 1) reasons.push(`DIMENSION_HASH_MISSING:${id}`);
    if (!finiteNumber(d.ciLowerDifferencePp)) reasons.push(`CI_LOWER_DIFF_MISSING:${id}`);
    if (finiteNumber(d.ciLowerDifferencePp) && Number(d.ciLowerDifferencePp) < -margin) reasons.push(`NON_INFERIORITY_NOT_PROVEN:${id}`);
    if (finiteScore(d.arbm) && finiteScore(d.codex) && Number(d.arbm) + margin / 100 < Number(d.codex)) reasons.push(`BELOW_CODEX_MARGIN:${id}`);
  }

  const pass = reasons.length === 0;
  return {
    schema: 'arbm-codex-parity-gate-v2',
    policy: 'CODEX_PARITY_HARD_FLOOR+ZERO_SPEND_HARD',
    pass,
    release: pass ? 'PARITY_GATE_PASS' : 'BLOCKED',
    reasons,
  };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const file = process.argv[2];
  if (!file) {
    console.error('usage: node codex-parity-gate.mjs <evidence.json>');
    process.exit(64);
  }
  let evidence;
  try { evidence = JSON.parse(fs.readFileSync(file, 'utf8')); }
  catch (err) {
    console.error(JSON.stringify({schema:'arbm-codex-parity-gate-v2',pass:false,release:'BLOCKED',reasons:['EVIDENCE_READ_FAILED'],error:String(err.message || err)}));
    process.exit(65);
  }
  const result = evaluateCodexParity(evidence);
  console.log(JSON.stringify(result, null, 2));
  process.exit(result.pass ? 0 : 2);
}
