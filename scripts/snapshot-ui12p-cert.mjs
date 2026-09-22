import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import crypto from "node:crypto";
import { spawnSync, spawn } from "node:child_process";

const SAFE_PATH=/^[A-Za-z0-9._\-/]{1,260}$/;
const BLOCKED=/(^|\/)(?:\.env(?:\.|$)|id_rsa(?:\.|$)|credentials?(?:\.|$)|.*\.(?:pem|p12|pfx)$|service-account.*\.json$)/i;

function required(name){
  const value=String(process.env[name]||"").trim();
  if(!value) throw new Error(`missing_${name}`);
  return value;
}
function run(command,args,cwd,env=process.env,timeout=900000){
  const r=spawnSync(command,args,{cwd,env,encoding:"utf8",stdio:"pipe",timeout,shell:false});
  process.stdout.write(r.stdout||"");
  process.stderr.write(r.stderr||"");
  if(r.error) throw r.error;
  if(r.status!==0) throw new Error(`command_failed:${command}:${r.status}`);
}
function gitBlobSha(bytes){
  const header=Buffer.from(`blob ${bytes.length}\0`);
  return crypto.createHash("sha1").update(header).update(bytes).digest("hex");
}
async function fetchSnapshot(){
  const base=required("ARBM_SNAPSHOT_REST_URL");
  const apiKey=required("ARBM_SNAPSHOT_API_KEY");
  const proofToken=required("ARBM_SNAPSHOT_PROOF_TOKEN");
  const response=await fetch(base,{
    headers:{
      apikey:apiKey,
      "x-arbm-proof-token":proofToken,
      accept:"application/json",
    },
    signal:AbortSignal.timeout(30000),
  });
  if(!response.ok){const body=(await response.text()).slice(0,500);throw new Error(`snapshot_http_${response.status}:${body}`);}
  const rows=await response.json();
  if(!Array.isArray(rows)||!rows.length) throw new Error("snapshot_empty");
  return rows;
}
export async function runSnapshotUi12pCert(){
  const expectedSha=required("ARBM_EXPECTED_SHA").toLowerCase();
  const expectedDigest=required("ARBM_SNAPSHOT_PACKAGE_DIGEST").toLowerCase();
  const expectedCount=Number(required("ARBM_SNAPSHOT_FILE_COUNT"));
  const rows=await fetchSnapshot();
  if(rows.length!==expectedCount) throw new Error(`snapshot_count_mismatch:${rows.length}:${expectedCount}`);

  const normalized=rows.map((row)=>{
    const rel=String(row.path||"");
    if(!SAFE_PATH.test(rel)||rel.includes("..")||rel.startsWith("/")||BLOCKED.test(rel)) throw new Error(`unsafe_path:${rel}`);
    const bytes=Buffer.from(String(row.content_b64||""),"base64");
    const size=Number(row.size_bytes);
    if(bytes.length!==size) throw new Error(`size_mismatch:${rel}`);
    const blob=gitBlobSha(bytes);
    if(blob!==String(row.blob_sha||"").toLowerCase()) throw new Error(`blob_mismatch:${rel}`);
    return {rel,bytes,blob};
  }).sort((a,b)=>a.rel.localeCompare(b.rel));

  const digest=crypto.createHash("sha256").update(normalized.map((x)=>`${x.rel}:${x.blob}`).join("\n")).digest("hex");
  if(digest!==expectedDigest) throw new Error(`package_digest_mismatch:${digest}`);

  const root=fs.mkdtempSync(path.join(os.tmpdir(),"arbm-ui12p-"));
  for(const item of normalized){
    const target=path.join(root,item.rel);
    fs.mkdirSync(path.dirname(target),{recursive:true});
    fs.writeFileSync(target,item.bytes);
  }

  console.log(JSON.stringify({marker:"ARBM_UI12P_SNAPSHOT_PROVENANCE",sha:expectedSha,digest,fileCount:normalized.length}));

  const env={...process.env,ARBM_EXPECTED_SHA:expectedSha,NODE_OPTIONS:"--max-old-space-size=2048"};
  run("npm",["ci","--ignore-scripts","--no-audit","--no-fund"],root,env);
  run("npm",["run","typecheck"],root,env);
  run("node",["--test",
    "tests/theme-global-pdv-v1.test.mjs",
    "tests/visual-12p-global-contract-v1.test.mjs",
    "tests/pdv-visual-baseline-v1.test.mjs",
    "tests/authenticated-production-visual-contract-v1.test.mjs",
    "tests/ui-viewport-surgical-no-cut-v1.test.mjs",
    "tests/ui-phase-b-accessibility.test.mjs",
    "tests/ci-quorum-deadlock-v1.test.mjs",
  ],root,env);
  run("npm",["run","lint"],root,env);
  run("npm",["run","check:cloudflare"],root,env);
  run("npx",["playwright","install","chromium"],root,env,600000);

  const candidates=fs.readdirSync(path.join(root,"cf-release-bundle")).filter((name)=>name.endsWith(".js"));
  if(!candidates.length) throw new Error("cloudflare_entry_missing");
  const entry=path.join(root,"cf-release-bundle",candidates[0]);
  const wrangler=spawn("npx",["wrangler","dev",entry,"--local","--local-protocol","https","--port","3000","--config","wrangler.jsonc"],{
    cwd:root,env,stdio:["ignore","pipe","pipe"],shell:false,
  });
  let runtimeLog="";
  wrangler.stdout.on("data",(d)=>{runtimeLog+=d.toString();});
  wrangler.stderr.on("data",(d)=>{runtimeLog+=d.toString();});
  try{
    let ready=false;
    for(let i=0;i<90;i++){
      try{
        const res=await fetch("https://127.0.0.1:3000/login",{signal:AbortSignal.timeout(2000)});
        if(res.status===200){ready=true;break;}
      }catch{}
      await new Promise((resolve)=>setTimeout(resolve,1000));
    }
    if(!ready) throw new Error("candidate_startup_failed:"+runtimeLog.slice(-4000));
    run("node",["scripts/audit-pr-public-visual.mjs"],root,{...env,ARBM_PR_BASE_URL:"https://127.0.0.1:3000"},600000);
  } finally {
    wrangler.kill("SIGTERM");
  }
  console.log(JSON.stringify({marker:"ARBM_UI12P_REMOTE_CERTIFICATION",state:"PASS",sha:expectedSha,digest}));
}
