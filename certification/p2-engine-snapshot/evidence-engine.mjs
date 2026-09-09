import crypto from 'node:crypto';

export const REQUIRED_TECHNICAL_GATES = Object.freeze([
  'tests','lint','typecheck','build','security','remoteExecution','localFallback',
  'lowMemoryRemote','costFirewall','secretIsolation','abort','resume','recovery',
  'rollback','constitution','runtimeControl','capabilityGrant','capabilityGrantAuth','resourceGovernor','observability','agenticRedTeam'
]);

function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map(k => [k, canonicalize(value[k])]));
  }
  return value;
}
export function evidenceManifest({ missionId = '', gates = {}, artifacts = [], metrics = {}, cost = {} } = {}) {
  const normalized = canonicalize({
    schema: 'arbm-evidence-v2',
    missionId: String(missionId),
    createdAt: new Date().toISOString(),
    gates,
    artifacts,
    metrics,
    cost: {
      mandatorySpendBRL: Number(cost.mandatorySpendBRL),
      paidFallbackUsed: cost.paidFallbackUsed === true
    }
  });
  const canonical = JSON.stringify(normalized);
  return { ...normalized, sha256: crypto.createHash('sha256').update(canonical).digest('hex') };
}

export function evidencePass(manifest = {}, required = REQUIRED_TECHNICAL_GATES) {
  const gates = manifest.gates || {};
  const requiredPass = required.every(name => gates[name] === true);
  const finiteZero = Number.isFinite(manifest.cost?.mandatorySpendBRL) && manifest.cost.mandatorySpendBRL === 0;
  return requiredPass && finiteZero && manifest.cost?.paidFallbackUsed === false;
}
