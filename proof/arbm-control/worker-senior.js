import oauthWorker from './worker-oauth.js';

const TELEMETRY_REPOS = [
  { label: 'ARBM ONE', repo: 'arbmsistone-lab/ARBM-one' },
  { label: 'ARBM SIST', repo: 'arbmsistone-lab/arbm-sist-external-exec-proof' },
  { label: 'ZEVANORY', repo: 'arbmsistone-lab/zevanory-public-mirror' },
  { label: 'ARBM CONTROL', repo: 'arbmsistone-lab/arbm-control' },
  { label: 'ARBM CONTROL App', repo: 'arbmsistone-lab/credicontrol-pro' },
];

const PROBES = [
  { label: 'ARBM ONE', url: 'https://arbmone.api.br/' },
  { label: 'ZEVANORY', url: 'https://zevanory.api.br/' },
  { label: 'ZEVANORY EDGE', url: 'https://edge.zevanory.api.br/' },
  { label: 'ARBM CONTROL', url: 'https://arbm-control.zevanory.workers.dev/health' },
];

function responseJson(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'no-store',
      'access-control-allow-origin': '*',
    },
  });
}

async function github(env, path) {
  const response = await fetch(`https://api.github.com${path}`, {
    headers: {
      Accept: 'application/vnd.github+json',
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      'X-GitHub-Api-Version': '2022-11-28',
      'User-Agent': 'ARBM-CONTROL-SENIOR',
    },
  });
  if (!response.ok) {
    throw new Error(`GitHub ${response.status}`);
  }
  return response.json();
}

function compactCheck(item) {
  return {
    name: item.name || item.context || 'unknown',
    status: item.status || item.state || null,
    conclusion: item.conclusion || null,
    url: item.html_url || item.target_url || null,
  };
}

function classifyEvidence(checks, statuses, runs) {
  const all = [...checks.map(compactCheck), ...statuses.map(compactCheck)];
  const matches = pattern => all.filter(item => pattern.test(item.name));
  const runMatches = pattern => runs.filter(run => pattern.test(run.name || ''));
  return {
    external_ci: matches(/buildkite|circleci|vercel|cloudflare/i),
    e2e: [
      ...matches(/e2e|playwright|cypress|synthetic|browser|integration/i),
      ...runMatches(/e2e|playwright|cypress|synthetic|browser|integration/i).map(run => ({
        name: run.name,
        status: run.status,
        conclusion: run.conclusion,
        url: run.html_url,
      })),
    ].slice(0, 12),
    recovery: runMatches(/recovery|restore|rollback|drill|continuity|backup/i).map(run => ({
      name: run.name,
      status: run.status,
      conclusion: run.conclusion,
      url: run.html_url,
    })).slice(0, 12),
  };
}

async function repoTelemetry(env, spec) {
  try {
    const meta = await github(env, `/repos/${spec.repo}`);
    const branch = await github(env, `/repos/${spec.repo}/branches/${encodeURIComponent(meta.default_branch)}`);
    const sha = branch.commit.sha;
    const [runsData, statusData, checksData] = await Promise.all([
      github(env, `/repos/${spec.repo}/actions/runs?per_page=10`),
      github(env, `/repos/${spec.repo}/commits/${sha}/status`),
      github(env, `/repos/${spec.repo}/commits/${sha}/check-runs?per_page=100`),
    ]);
    const runs = (runsData.workflow_runs || []).map(run => ({
      id: run.id,
      name: run.name,
      status: run.status,
      conclusion: run.conclusion,
      head_sha: run.head_sha,
      branch: run.head_branch,
      event: run.event,
      created_at: run.created_at,
      html_url: run.html_url,
    }));
    const statuses = (statusData.statuses || []).map(compactCheck);
    const checks = (checksData.check_runs || []).map(compactCheck);
    const evidence = classifyEvidence(checksData.check_runs || [], statusData.statuses || [], runsData.workflow_runs || []);
    return {
      label: spec.label,
      source: 'arbm-control-private',
      default_branch: meta.default_branch,
      sha,
      visibility: meta.visibility,
      archived: !!meta.archived,
      combined_state: statusData.state || 'unknown',
      checks: checks.slice(0, 20),
      statuses: statuses.slice(0, 20),
      runs,
      external_ci: evidence.external_ci,
      e2e: evidence.e2e,
      recovery: evidence.recovery,
      ok: true,
    };
  } catch (error) {
    return {
      label: spec.label,
      source: 'arbm-control-private',
      ok: false,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

async function productionProbe(spec) {
  const started = Date.now();
  try {
    const response = await fetch(spec.url, {
      method: 'GET',
      redirect: 'follow',
      headers: { Accept: 'application/json,text/plain,text/html;q=0.8' },
      signal: AbortSignal.timeout(10000),
    });
    return {
      label: spec.label,
      url: spec.url,
      final_url: response.url,
      status: response.status,
      ok: response.ok,
      latency_ms: Date.now() - started,
      cf_ray: response.headers.get('cf-ray'),
    };
  } catch (error) {
    return {
      label: spec.label,
      url: spec.url,
      status: 0,
      ok: false,
      latency_ms: Date.now() - started,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

async function buildTelemetry(env) {
  const generatedAt = new Date().toISOString();
  const [repositories, production] = await Promise.all([
    Promise.all(TELEMETRY_REPOS.map(spec => repoTelemetry(env, spec))),
    Promise.all(PROBES.map(productionProbe)),
  ]);
  return {
    schema: 'arbm-control-telemetry/v1',
    generated_at: generatedAt,
    policy: {
      zero_spend: true,
      fail_closed: true,
      destructive_actions: false,
      source: 'ARBM CONTROL private connector',
    },
    repositories,
    production,
  };
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === '/telemetry/v1' && request.method === 'GET') {
      const telemetry = await buildTelemetry(env);
      return responseJson(telemetry);
    }
    return oauthWorker.fetch(request, env, ctx);
  },
};
