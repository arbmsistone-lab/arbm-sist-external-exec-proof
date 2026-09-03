import crypto from 'node:crypto';

const clean = (value) => String(value ?? '')
  .replace(/\u001b\[[0-9;]*m/g, '')
  .trim();

const digest = (value) => `sha256:${crypto.createHash('sha256').update(value).digest('hex')}`;

export const TASKS = [
  {
    id: 'add-bug',
    prompt: 'Fix function add(a,b){return a-b}. Return only corrected JavaScript.',
    validate: (out) => /function\s+add\s*\(\s*a\s*,\s*b\s*\)/.test(out)
      && /return\s+a\s*\+\s*b\s*;?/.test(out)
      && !/return\s+a\s*-\s*b/.test(out),
  },
  {
    id: 'factorial',
    prompt: 'Write JavaScript function factorial(n) recursively. Return only code.',
    validate: (out) => /function\s+factorial\s*\(\s*n\s*\)/.test(out)
      && /(n\s*<=\s*1|n\s*===?\s*[01])/.test(out)
      && /return\s+n\s*\*\s*factorial\s*\(\s*n\s*-\s*1\s*\)/.test(out),
  },
  {
    id: 'dedupe',
    prompt: 'Write a JavaScript expression returning unique values from array a. Return only expression.',
    validate: (out) => /(\.\.\.\s*new\s+Set\s*\(\s*a\s*\)|Array\.from\s*\(\s*new\s+Set\s*\(\s*a\s*\)\s*\))/.test(out),
  },
  {
    id: 'promise',
    prompt: 'Write JavaScript that awaits Promise.resolve(7) inside async function f. Return only code.',
    validate: (out) => /async\s+function\s+f\s*\(/.test(out)
      && /await\s+Promise\.resolve\s*\(\s*7\s*\)/.test(out),
  },
];

export function assessRun({ status, error, stdout, stderr, validate, latencyMs }) {
  const out = clean(stdout);
  const err = clean(stderr);
  const processError = error?.code || null;
  const outputChars = out.length;
  const integrity = status === 0 && !processError && outputChars > 0 && outputChars <= 8192;
  const semanticPass = integrity && validate(out);
  let failureClass = 'ok';
  if (processError === 'ETIMEDOUT') failureClass = 'timeout';
  else if (status !== 0 || processError) failureClass = 'runtime_error';
  else if (outputChars === 0) failureClass = 'empty_output';
  else if (outputChars > 8192) failureClass = 'oversized_output';
  else if (!semanticPass) failureClass = 'semantic_miss';

  return {
    exitCode: status,
    processError,
    latencyMs,
    outputChars,
    stderrChars: err.length,
    pass: semanticPass,
    integrity,
    failureClass,
    outputDigest: digest(out),
    stderrDigest: digest(err),
    stderrPreview: err.slice(0, 500),
  };
}

export function summarize(model, runtimeCommit, rows) {
  return {
    schema: 'arbm-shadow-lab-v4',
    model,
    runtimeCommit,
    rows,
    pass: rows.filter((row) => row.pass).length,
    total: rows.length,
    evaluatorIntegrity: rows.every((row) => row.integrity),
  };
}
