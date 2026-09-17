#!/usr/bin/env node

// Per-site control-plane verifier mirroring Task-Web/OSWorld-web
// scripts/verify-control-plane.mjs at website commit
// 60c89fe6a8ed934668619d8d26132848239eb8ee (blob 240a0d0f...).
// This is a preparation/readiness check only; it does not execute OSWorld tasks.

import assert from "node:assert/strict";
import fs from "node:fs";

const site = process.env.OSWORLD_SITE;
const host = process.env.OSWORLD_HOST;
const hostSuffix = process.env.OSWORLD_HOST_SUFFIX || "localhost";
const scheme = process.env.OSWORLD_SCHEME || "http";
const evidenceDir = process.env.EVIDENCE_DIR || ".";

assert.ok(site, "OSWORLD_SITE missing");
assert.ok(host, "OSWORLD_HOST missing");

const runId = `${Date.now().toString(36)}-${process.pid}`;
const origin = `${scheme}://${host}.${hostSuffix}`;
const cookie = `control-plane-${runId}-${site}`;
const isolatedCookie = `${cookie}-isolated`;
const endpoint = `${origin}/api/state?cookie=${encodeURIComponent(cookie)}`;

async function request(url, options = {}) {
  const response = await fetch(url, {
    redirect: "manual",
    ...options,
    headers: {
      ...(options.body ? { "content-type": "application/json" } : {}),
      ...(options.headers || {}),
    },
  });
  const text = await response.text();
  return { response, text };
}

function parseJson(result, context) {
  try {
    return JSON.parse(result.text);
  } catch {
    throw new Error(`${context} returned non-JSON ${result.response.status}: ${result.text.slice(0, 300)}`);
  }
}

function expectStateResponse(result, expectedCookie, context) {
  assert.equal(result.response.status, 200, `${context}: ${result.text.slice(0, 300)}`);
  const body = parseJson(result, context);
  assert.equal(body.user_id, expectedCookie, `${context}: wrong user_id`);
  assert.ok(body.state && typeof body.state === "object", `${context}: missing state envelope`);
  assert.ok(body.state.data && typeof body.state.data === "object", `${context}: missing state.data`);
  return body;
}

async function waitReady() {
  const readinessCookie = `readiness-${runId}-${site}`;
  const readinessEndpoint = `${origin}/api/state?cookie=${encodeURIComponent(readinessCookie)}`;
  for (let attempt = 1; attempt <= 60; attempt += 1) {
    try {
      const root = await request(`${origin}/`);
      const state = await request(readinessEndpoint);
      if (root.response.status >= 200 && root.response.status < 500 && state.response.status === 200) {
        fs.writeFileSync(`${evidenceDir}/readiness-attempt.txt`, `${attempt}\n`);
        fs.writeFileSync(`${evidenceDir}/readiness-state.json`, state.text);
        return;
      }
    } catch {
      // Retry while the official runtime warms up.
    }
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
  throw new Error(`${site}: frontend/control-plane did not become ready`);
}

await waitReady();

const putResult = await request(endpoint, {
  method: "PUT",
  body: JSON.stringify({
    data: { control_plane_probe: { left: 1 }, preserved_sibling: true },
    note: "control-plane compatibility probe",
  }),
});
const put = expectStateResponse(putResult, cookie, `${site} PUT`);
assert.deepEqual(put.state.data.control_plane_probe, { left: 1 }, `${site}: PUT data changed`);
assert.equal(put.state.data.preserved_sibling, true, `${site}: PUT sibling changed`);

const setCookie = putResult.response.headers.get("set-cookie") || "";
assert.match(setCookie, new RegExp(`(?:^|[;,]\\s*)user_id=${cookie}(?:;|$)`), `${site}: user_id cookie missing`);

const get = expectStateResponse(await request(endpoint), cookie, `${site} GET`);
assert.deepEqual(get, put, `${site}: GET response does not reproduce PUT state`);

if (site === "overleaf_collab_web") {
  for (const method of ["PUT", "PATCH", "DELETE"]) {
    const locked = await request(endpoint, {
      method,
      ...(method === "DELETE" ? {} : { body: JSON.stringify({ data: { blocked_probe: true } }) }),
    });
    assert.equal(locked.response.status, 403, `${site}: initialized ${method} was not locked`);
    assert.equal(parseJson(locked, `${site} locked ${method}`).code, "state_locked");
  }

  const cookieGet = expectStateResponse(
    await request(`${origin}/api/state`, { headers: { cookie: `user_id=${cookie}` } }),
    cookie,
    `${site} cookie GET`,
  );
  assert.deepEqual(cookieGet.state.data, put.state.data, `${site}: cookie did not reuse query-seeded state`);

  const unrestrictedCookie = `${cookie}-unrestricted`;
  const unrestrictedEndpoint = `${origin}/api/state?cookie=${encodeURIComponent(unrestrictedCookie)}`;
  const firstPatch = expectStateResponse(
    await request(unrestrictedEndpoint, {
      method: "PATCH",
      body: JSON.stringify({ data: { control_plane_probe: { left: 1 }, preserved_sibling: true } }),
    }),
    unrestrictedCookie,
    `${site} unrestricted PATCH`,
  );
  assert.deepEqual(firstPatch.state.data.control_plane_probe, { left: 1 });
  const patch = expectStateResponse(
    await request(unrestrictedEndpoint, {
      method: "PATCH",
      body: JSON.stringify({ data: { control_plane_probe: { right: 2 } } }),
    }),
    unrestrictedCookie,
    `${site} unrestricted deep-merge PATCH`,
  );
  assert.deepEqual(patch.state.data.control_plane_probe, { left: 1, right: 2 });
  assert.equal(patch.state.data.preserved_sibling, true);
  const removed = expectStateResponse(
    await request(unrestrictedEndpoint, { method: "DELETE" }),
    unrestrictedCookie,
    `${site} unrestricted DELETE`,
  );
  assert.equal(Object.hasOwn(removed.state.data, "control_plane_probe"), false);
} else {
  const patch = expectStateResponse(
    await request(endpoint, {
      method: "PATCH",
      body: JSON.stringify({
        data: { control_plane_probe: { right: 2 } },
        note: "control-plane deep-merge probe",
      }),
    }),
    cookie,
    `${site} PATCH`,
  );
  assert.deepEqual(
    patch.state.data.control_plane_probe,
    { left: 1, right: 2 },
    `${site}: PATCH no longer deep-merges nested objects`,
  );
  assert.equal(patch.state.data.preserved_sibling, true, `${site}: PATCH removed an unrelated field`);

  const cookieGet = expectStateResponse(
    await request(`${origin}/api/state`, { headers: { cookie: `user_id=${cookie}` } }),
    cookie,
    `${site} cookie GET`,
  );
  assert.deepEqual(cookieGet.state.data, patch.state.data, `${site}: cookie did not reuse query-seeded state`);

  const removed = expectStateResponse(await request(endpoint, { method: "DELETE" }), cookie, `${site} DELETE`);
  assert.equal(
    Object.hasOwn(removed.state.data, "control_plane_probe"),
    false,
    `${site}: DELETE did not reset state`,
  );
  const afterDelete = expectStateResponse(await request(endpoint), cookie, `${site} GET after DELETE`);
  assert.deepEqual(afterDelete, removed, `${site}: reset state was not persisted`);
}

const isolated = expectStateResponse(
  await request(`${origin}/api/state?cookie=${encodeURIComponent(isolatedCookie)}`),
  isolatedCookie,
  `${site} isolated GET`,
);
assert.equal(
  Object.hasOwn(isolated.state.data, "control_plane_probe"),
  false,
  `${site}: state leaked across cookies`,
);

for (const pathname of ["/state-manage", "/state-manage/", "/state-doc", "/state-doc/"]) {
  const result = await request(`${origin}${pathname}`, { redirect: "follow" });
  assert.equal(result.response.status, 404, `${site}: ${pathname} remains publicly reachable`);
  assert.doesNotMatch(result.text, /\/api\/state(?:\/|[?"']|$)/i, `${site}: ${pathname} discloses control-plane path`);
}

for (const pathname of ["/", "/api/openapi.json", "/api/docs", "/api/redoc"]) {
  const result = await request(`${origin}${pathname}`);
  assert.doesNotMatch(
    result.text,
    /\/api\/state(?:\/|[?"']|$)/i,
    `${site}: ${pathname} publicly discloses control-plane path`,
  );
  if (
    pathname === "/api/openapi.json" &&
    result.response.status === 200 &&
    (result.response.headers.get("content-type") || "").includes("application/json")
  ) {
    const schema = parseJson(result, `${site} public OpenAPI`);
    assert.equal(
      Object.keys(schema.paths || {}).some((path) => /^\/api\/state(?:\/|$)/.test(path)),
      false,
      `${site}: public OpenAPI includes a control-plane path`,
    );
    assert.equal(
      (schema.tags || []).some((tag) => String(tag?.name).toLowerCase() === "state"),
      false,
      `${site}: public OpenAPI includes a generic state tag`,
    );
  }
}

const verdict = {
  status: "PASS",
  site,
  host,
  host_suffix: hostSuffix,
  upstream_contract: "Task-Web/OSWorld-web scripts/verify-control-plane.mjs",
  upstream_website_commit: "60c89fe6a8ed934668619d8d26132848239eb8ee",
  upstream_contract_blob: "240a0d0f172e5bf59f492f6db54485f2011288ea",
  benchmark_tasks_started: 0,
};
fs.writeFileSync(`${evidenceDir}/verdict.json`, JSON.stringify(verdict, null, 2) + "\n");
process.stdout.write(`PASS ${site}\n`);
