import fs from 'node:fs';

const readJson = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));
const sha40 = (x) => /^[a-f0-9]{40}$/.test(String(x || '').toLowerCase());
const sha256 = (x) => /^sha256:[a-f0-9]{64}$/.test(String(x || '').toLowerCase());

export function verifyP8ReproProof(evidence, attempts, jobs, artifacts, agent) {
  const reasons = [];
  const p8 = evidence?.p8Evidence || {};
  if (evidence?.p8Complete !== true) reasons.push('P8_COMPLETE_FLAG_MISSING');
  if (!Number.isInteger(p8.runId) || p8.runId <= 0) reasons.push('P8_RUN_ID_INVALID');
  if (!sha40(p8.headSha)) reasons.push('P8_HEAD_SHA_INVALID');
  if (!Array.isArray(p8.successfulAttempts) || p8.successfulAttempts.length < 2) reasons.push('P8_REPRO_ATTEMPTS_MISSING');

  const requiredSteps = ['Generation evidence gate','Run official evaluator on clean public sample task','Freeze hashes','Upload immutable smoke evidence'];
  for (const n of p8.successfulAttempts || []) {
    const a = attempts?.[String(n)];
    if (!a || a.id !== p8.runId || a.run_attempt !== n || a.status !== 'completed' || a.conclusion !== 'success' || a.head_sha !== p8.headSha) reasons.push(`P8_ATTEMPT_INVALID:${n}`);
    const js = jobs?.[String(n)]?.jobs || [];
    const job = js.find((j) => j.name === 'real-smoke');
    if (!job || job.conclusion !== 'success' || job.head_sha !== p8.headSha) reasons.push(`P8_JOB_INVALID:${n}`);
    const byName = new Map((job?.steps || []).map((s) => [s.name, s.conclusion]));
    for (const step of requiredSteps) if (byName.get(step) !== 'success') reasons.push(`P8_STEP_INVALID:${n}:${step}`);
  }

  const artifact = (artifacts?.artifacts || []).find((a) => a.name === p8.artifactName);
  if (!artifact || artifact.expired === true || !sha256(artifact.digest)) reasons.push('P8_ARTIFACT_DIGEST_INVALID');
  if (agent?.validPatch !== true || Number(agent?.exitCode) !== 0) reasons.push('P8_AGENT_EVIDENCE_INVALID');
  if (Number(agent?.providerCostUsd) !== 0) reasons.push('P8_PROVIDER_COST_NOT_ZERO');
  if (agent?.goldPatchExposedToAgent !== false) reasons.push('P8_GOLD_PATCH_FIREWALL_INVALID');
  if (agent?.sourceCommit !== p8.headSha) reasons.push('P8_AGENT_SHA_MISMATCH');
  return {pass: reasons.length === 0, reasons, runId:p8.runId, headSha:p8.headSha, artifactDigest:artifact?.digest || null};
}

if (process.argv[1]?.endsWith('p8-repro-proof.mjs')) {
  const [evidenceFile, attempts1, attempts2, jobs1, jobs2, artifactsFile, agentFile] = process.argv.slice(2);
  if (![evidenceFile,attempts1,attempts2,jobs1,jobs2,artifactsFile,agentFile].every(Boolean)) process.exit(64);
  const evidence=readJson(evidenceFile);
  const attempts={'1':readJson(attempts1),'2':readJson(attempts2)};
  const jobs={'1':readJson(jobs1),'2':readJson(jobs2)};
  const result=verifyP8ReproProof(evidence,attempts,jobs,readJson(artifactsFile),readJson(agentFile));
  console.log(JSON.stringify(result,null,2));
  process.exit(result.pass ? 0 : 2);
}
