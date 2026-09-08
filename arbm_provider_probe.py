import json, os, urllib.request, urllib.error

API_URL = "https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-terminal-agent-v1"

def oidc():
    url = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
    token = os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request(url + sep + "audience=arbm-sist-benchmark", headers={"Authorization":"Bearer "+token})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())["value"]

def main():
    body = {"instruction":"Inspect the sandbox with pwd and report one safe first command as JSON.","observation":"No commands executed yet.","step":1}
    req = urllib.request.Request(API_URL, data=json.dumps(body).encode(), method="POST", headers={"Authorization":"Bearer "+oidc(),"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            data=json.loads(r.read().decode())
            safe={k:data.get(k) for k in ("ok","status","provider","model","provider_attempts","mandatory_cost_usd","paid_fallback_used")}
            print(json.dumps(safe,separators=(",",":")))
            if data.get("ok") is not True or data.get("mandatory_cost_usd") != 0 or data.get("paid_fallback_used") is not False: raise SystemExit(2)
    except urllib.error.HTTPError as e:
        data=json.loads(e.read().decode())
        safe={k:data.get(k) for k in ("status","error","provider_attempts","mandatory_cost_usd")}
        print(json.dumps(safe,separators=(",",":")))
        raise

if __name__ == "__main__": main()
# groq-probe-20260908 
# groq-json-only-probe-2 
