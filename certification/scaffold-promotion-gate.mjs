import fs from 'node:fs';
import { pathToFileURL } from 'node:url';

const readJson = p => JSON.parse(fs.readFileSync(p, 'utf8').replace(/^\uFEFF/, ''));
const defaultPolicy = readJson(new URL('./scaffold-promotion-policy.json', import.meta.url));
const mean = xs => xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0;
const trialKey = t => `${t.task}::${t.rep}`;
const exceptionRate = xs => xs.length ? xs.filter(t => t.exception).length / xs.length : 1;

function taskMeans(trials) {
  const map = new Map();
  for (const t of trials) {
    if (!map.has(t.task)) map.set(t.task, []);
    map.get(t.task).push(Number(t.reward || 0));
  }
  return new Map([...map].map(([k, v]) => [k, mean(v)]));
}

function samplingStats(trials) {
  const counts = new Map();
  for (const t of trials) counts.set(t.task, (counts.get(t.task) || 0) + 1);
  return {distinctTasks: counts.size, minRepetitions: counts.size ? Math.min(...counts.values()) : 0};
}

export function evaluateScaffoldPromotion(evidence, policy = defaultPolicy) {
  const errors = [];
  const comparability = evidence.comparability || {};
  for (const key of policy.comparabilityRequired || []) {
    if (comparability[key] !== true) errors.push(`comparability_${key}_required`);
  }
  const baseline = Array.isArray(evidence.baselineTrials) ? evidence.baselineTrials : [];
  const candidate = Array.isArray(evidence.candidateTrials) ? evidence.candidateTrials : [];
  if (!baseline.length || !candidate.length) errors.push('paired_trials_required');
  if (baseline.length !== candidate.length) errors.push('paired_trial_count_mismatch');

  const candidateByKey = new Map(candidate.map(t => [trialKey(t), t]));
  for (const b of baseline) {
    const c = candidateByKey.get(trialKey(b));
    if (!c) errors.push(`missing_candidate_pair_${trialKey(b)}`);
  }

  const baseMean = mean(baseline.map(t => Number(t.reward || 0)));
  const candMean = mean(candidate.map(t => Number(t.reward || 0)));
  const baseExc = exceptionRate(baseline);
  const candExc = exceptionRate(candidate);
  const baseSampling = samplingStats(baseline);
  const candSampling = samplingStats(candidate);
  const baseTaskMeans = taskMeans(baseline);
  const candTaskMeans = taskMeans(candidate);
  let improvedTasks = 0;
  let regressedTasks = 0;
  for (const [task, bMean] of baseTaskMeans) {
    const cMean = candTaskMeans.get(task) ?? -Infinity;
    if (cMean > bMean) improvedTasks += 1;
    if (cMean < bMean) regressedTasks += 1;
  }
  const improvedTaskFraction = baseTaskMeans.size ? improvedTasks / baseTaskMeans.size : 0;
  const regressedTaskFraction = baseTaskMeans.size ? regressedTasks / baseTaskMeans.size : 1;
  const gain = policy.reproducibleGain;
  const samplingPass = baseSampling.distinctTasks >= gain.minDistinctTasks &&
    candSampling.distinctTasks >= gain.minDistinctTasks &&
    baseSampling.minRepetitions >= gain.minRepetitionsPerTask &&
    candSampling.minRepetitions >= gain.minRepetitionsPerTask;
  const reproducibleGain = samplingPass &&
    (candMean - baseMean) >= gain.minAbsoluteMeanGain &&
    improvedTaskFraction >= gain.minImprovedTaskFraction &&
    (candExc - baseExc) <= gain.maxExceptionRateIncrease;

  const failures = evidence.failureModes || {};
  const eliminated = policy.failureModeElimination.requiredModes.every(mode =>
    Number(failures?.baseline?.[mode] || 0) > 0 &&
    Number(failures?.candidate?.[mode] || 0) <= policy.failureModeElimination.candidateAllowedCountPerMode
  );
  const failureModeElimination = eliminated &&
    (candMean - baseMean) >= -policy.failureModeElimination.maxMeanRewardRegression &&
    (candExc - baseExc) <= policy.failureModeElimination.maxExceptionRateIncrease;

  const regression = evidence.regression || {};
  const zeroRegression = regression.allExistingGatesPass === true &&
    regressedTaskFraction <= policy.regression.maxRegressedTaskFraction &&
    Number(regression.newP0 || 0) <= policy.regression.allowNewP0 &&
    Number(regression.newP1 || 0) <= policy.regression.allowNewP1 &&
    Number(regression.newP2 || 0) <= policy.regression.allowNewP2;

  const pass = errors.length === 0 && zeroRegression && (reproducibleGain || failureModeElimination);
  return {schema:'arbm-scaffold-promotion-gate-result-v1', pass, reproducibleGain,
    failureModeElimination, zeroRegression, metrics:{baseMean,candMean,absoluteMeanGain:candMean-baseMean,
    baseExceptionRate:baseExc,candidateExceptionRate:candExc,improvedTaskFraction,regressedTaskFraction,baseSampling,candSampling}, errors};
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const evidencePath = process.argv[2];
  if (!evidencePath) throw new Error('usage: node scaffold-promotion-gate.mjs <evidence.json>');
  const result = evaluateScaffoldPromotion(readJson(evidencePath));
  console.log(JSON.stringify(result, null, 2));
  if (!result.pass) process.exit(1);
}
