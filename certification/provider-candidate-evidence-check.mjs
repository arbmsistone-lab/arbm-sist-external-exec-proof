import fs from 'node:fs';
const p = new URL('./provider-candidate-evidence.json', import.meta.url);
const d = JSON.parse(fs.readFileSync(p, 'utf8'));
const errors = [];
if (d?.policy?.zeroSpendHard !== true) errors.push('zeroSpendHard_must_be_true');
if (d?.policy?.heavyExecution !== 'REMOTE_ONLY') errors.push('heavyExecution_must_be_REMOTE_ONLY');
if (d?.policy?.failClosed !== true) errors.push('failClosed_must_be_true');
if (!Array.isArray(d?.candidates) || d.candidates.length === 0) errors.push('candidates_required');
for (const c of d.candidates ?? []) {
  if (!c.id) errors.push('candidate_missing_id');
  if (!['DISCOVERED','QUALIFIED_CANDIDATE','LIVE_PROVED','ACTIVE'].includes(c.state)) errors.push(`${c.id}:invalid_state`);
  if (c.state === 'ACTIVE') errors.push(`${c.id}:ACTIVE_forbidden_in_candidate_registry`);
  if (!Array.isArray(c.sources) || c.sources.length === 0) errors.push(`${c.id}:sources_required`);
  if (!Array.isArray(c.unresolved)) errors.push(`${c.id}:unresolved_required`);
}
const out = {schema:'arbm-provider-candidate-evidence-check-v1', pass:errors.length===0, candidates:d.candidates?.length??0, errors};
console.log(JSON.stringify(out,null,2));
if (errors.length) process.exit(1);
