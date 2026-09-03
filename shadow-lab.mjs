import { spawnSync } from 'node:child_process';
import { TASKS, assessRun, summarize } from './shadow-evaluator.mjs';

const cli = process.env.LLAMA_CLI;
const model = process.env.MODEL_PATH;
const label = process.env.MODEL_LABEL || 'unknown';
const runtimeCommit = '159b741427337a2e9a58b08121001545d66b5825';

if (!cli || !model) throw new Error('runtime_required');

const args = [
  '-n', '160',
  '--temp', '0',
  '--no-display-prompt',
  '--no-show-timings',
  '--simple-io',
  '--single-turn',
  '--log-colors', 'off',
  '--no-log-prefix',
  '--no-log-timestamps',
];

const rows = [];
for (const task of TASKS) {
  const started = Date.now();
  const run = spawnSync(cli, ['-m', model, '-p', task.prompt, ...args], {
    encoding: 'utf8',
    timeout: 180000,
    maxBuffer: 512 * 1024,
  });
  rows.push({
    id: task.id,
    ...assessRun({
      status: run.status,
      error: run.error,
      stdout: run.stdout,
      stderr: run.stderr,
      validate: task.validate,
      latencyMs: Date.now() - started,
    }),
  });
}

const result = summarize(label, runtimeCommit, rows);
console.log(JSON.stringify(result));
process.exit(result.pass === result.total && result.evaluatorIntegrity ? 0 : 1);
