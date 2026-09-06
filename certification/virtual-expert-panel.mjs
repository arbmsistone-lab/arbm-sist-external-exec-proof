import fs from 'node:fs';

const cfg = JSON.parse(fs.readFileSync(new URL('./virtual-expert-panel.json', import.meta.url)));
const required = Number(cfg.requiredExperts || 0);
const experts = Array.isArray(cfg.experts) ? cfg.experts : [];
const ids = experts.map(x => x.id);
const unique = new Set(ids);

const errors = [];
if (cfg.failClosed !== true) errors.push('failClosed_must_be_true');
if (cfg.consensus !== 'ALL_REQUIRED_PASS') errors.push('consensus_must_be_ALL_REQUIRED_PASS');
if (required !== 20) errors.push(`requiredExperts_expected_20_got_${required}`);
if (experts.length !== required) errors.push(`expert_count_${experts.length}_required_${required}`);
if (unique.size !== experts.length) errors.push('duplicate_expert_ids');
for (const e of experts) {
  if (!e?.id || !e?.focus) errors.push('expert_missing_id_or_focus');
}

const result = {
  schema: 'arbm-virtual-expert-panel-check-v1',
  pass: errors.length === 0,
  requiredExperts: required,
  observedExperts: experts.length,
  consensus: cfg.consensus,
  failClosed: cfg.failClosed,
  expertIds: ids,
  errors
};
console.log(JSON.stringify(result, null, 2));
if (errors.length) process.exit(1);
