"""Minimal live provider matrix. Does not execute generated actions or mutate plans."""
import json,os,urllib.request,urllib.error
from datetime import datetime,timezone
from pathlib import Path
from arbm_provider_probe import API,oidc
from mesh_capacity import certify
from sovereign_capacity_gate import certify_sovereign_capacity

fields=("route","model","status","parsed","usage_tokens","usage","retry_after","rate_limit_headers","mandatory_cost_usd","paid_fallback_used","shared_control","quota_kind","latency_ms")
def main():
    if os.environ.get("ZERO_SPEND_MODE")!="HARD":raise SystemExit("ZERO_SPEND_HARD_REQUIRED")
    token=oidc();proof=[]
    for provider in ("lightning","groq","google","mistral"):
        body={"instruction":"Return one safe directory inspection command as JSON.","observation":"No commands executed. Certification smoke only.","step":1,"provider_hint":provider}
        req=urllib.request.Request(API,data=json.dumps(body).encode(),method="POST",headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"})
        try:
            with urllib.request.urlopen(req,timeout=75) as r:http=r.status;data=json.loads(r.read())
        except urllib.error.HTTPError as e:
            http=e.code
            try:data=json.loads(e.read())
            except ValueError:data={}
        except (urllib.error.URLError,TimeoutError,ValueError):http=None;data={}
        attempts=[{k:a[k] for k in fields if k in a} for a in data.get("provider_attempts",[])]
        row={"timestamp_utc":datetime.now(timezone.utc).isoformat(),"requested_provider":provider,"http":http,"provider":data.get("provider"),"model":data.get("model"),"status":data.get("status"),"ok":data.get("ok"),"mandatory_cost_usd":data.get("mandatory_cost_usd"),"paid_fallback_used":data.get("paid_fallback_used"),"attempts":attempts,"run":os.environ.get("GITHUB_RUN_ID"),"tested_sha":os.environ.get("GITHUB_SHA")}
        row["live"]=http==200 and row['ok'] is True and row['status']=='PASS' and row['mandatory_cost_usd']==0 and row['paid_fallback_used'] is False and any(a.get('status')==200 and a.get('parsed') is True for a in attempts)
        proof.append(row);print(json.dumps(row,separators=(',',':')),flush=True)
    sovereign=certify_sovereign_capacity()
    result={"tested_sha":os.environ.get("GITHUB_SHA"),"run":os.environ.get("GITHUB_RUN_ID"),"providers":proof,"capacity":certify({}),"sovereign_capacity":sovereign,"admin_credential":"NOT_IDENTIFIED_IN_AUTHORIZED_SECRET_METADATA","account_evidence":"UNKNOWN"}
    Path('certification-output').mkdir(exist_ok=True)
    Path('certification-output/live-matrix.json').write_text(json.dumps(result,indent=2))
    gates={
        "LIVE_PROVIDERS": all(p['live'] for p in proof),
        "THREE_MILLION_PER_DAY": sovereign["status"] if sovereign["certified"] else "FAIL_INSUFFICIENT_QUANTITATIVE_EVIDENCE",
        "THREE_MILLION_PER_DAY_SCOPE": sovereign.get("scope"),
    }
    Path('certification-output/gates.json').write_text(json.dumps(gates,indent=2))
    return 0 if all(p['live'] for p in proof) and sovereign['certified'] else 2
if __name__=='__main__':raise SystemExit(main())
