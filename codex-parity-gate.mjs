import fs from 'node:fs';

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
const isoDate = (x) => typeof x === 'string' && !Number.isNaN(Date.parse(x));

export function evaluateCodexParity(evidence) {
  const reasons = [];
  const e = evidence && typeof evidence === 'object' ? evidence : {};
  const ref = e.reference && typeof e.reference === 'object' ? e.reference : {};
  if (ref.product !== 'OpenAI Codex') reasons.push('REFERENCE_PRODUCT_INVALID');
  if (!isoDate(ref.capturedAt)) reasons.push('REFERENCE_DATE_MISSING');
  if (!Array.isArray(ref.publicSources) || ref.publicSources.length < 1) reasons.push('REFERENCE_SOURCES_MISSING');
  if (e.zeroSpendHard !== true) reasons.push('ZERO_SPEND_POLICY_NOT_PROVEN');
  if (e.p8Complete !== true) reasons.push('P8_INCOMPLETE');
  if (e.p9IndependentAudit !== true) reasons.push('P9_INDEPENDENT_AUDIT_MISSING');
  if (e.failedRunsDisclosed !== true) reasons.push('FAILED_RUNS_NOT_DISCLOSED');
  if (e.rawArtifactsHashed !== true) reasons.push('RAW_ARTIFACT_HASHES_MISSING');
  if (e.noHiddenEvaluatorFeedback !== true) reasons.push('HIDDEN_EVALUATOR_FIREWALL_NOT_PROVEN');
  if (!Array.isArray(e.dimensions)) reasons.push('DIMENSIONS_MISSING');

  const byId = new Map((Array.isArray(e.dimensions) ? e.dimensions : []).map((d) => [d?.id, d]));
  for (const id of REQUIRED_DIMENSIONS) {
    const d = byId.get(id);
    if (!d) { reasons.push(`DIMENSION_MISSING:${id}`); continue; }
    if (!finiteScore(d.arbm)) reasons.push(`ARBM_SCORE_INVALID:${id}`);
    if (!finiteScore(d.codex)) reasons.push(`CODEX_SCORE_INVALID:${id}`);
    if (!Number.isInteger(d.samples) || d.samples < 3) reasons.push(`INSUFFICIENT_SAMPLES:${id}`);
    if (!Array.isArray(d.artifactSha256) || d.artifactSha256.length < 1) reasons.push(`DIMENSION_HASH_MISSING:${id}`);
    if (finiteScore(d.arbm) && finiteScore(d.codex) && Number(d.arbm) < Number(d.codex)) reasons.push(`BELOW_CODEX:${id}`);
  }

  const pass = reasons.length === 0;
  return {
    schema: 'arbm-codex-parity-gate-v1',
    policy: 'CODEX_PARITY_HARD_FLOOR+QUALITY_FIRST_ZERO_SPEND_HARD',
    pass,
    release: pass ? 'PARITY_GATE_PASS' : 'BLOCKED',
    reasons,
  };
}
if (import.meta.url === `file://${process.argv[1]?.replace(/\\/g,'/')}`) {
  const file = process.argv[2];
  if (!file) {
    console.error('usage: node codex-parity-gate.mjs <evidence.json>');
    process.exit(64);
  }
  let evidence;
  try { evidence = JSON.parse(fs.readFileSync(file, 'utf8')); }
  catch (err) {
    console.error(JSON.stringify({schema:'arbm-codex-parity-gate-v1',pass:false,release:'BLOCKED',reasons:['EVIDENCE_READ_FAILED'],error:String(err.message || err)}));
    process.exit(65);
  }
  const result = evaluateCodexParity(evidence);
  console.log(JSON.stringify(result, null, 2));
  process.exit(result.pass ? 0 : 2);
}
