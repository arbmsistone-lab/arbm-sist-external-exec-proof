"""OIDC-only inventory of external provider credential presence; never exposes values."""
import json, os, urllib.request
API="https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-ai-three-provider-probe-20260908"
def oidc():
    url=os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
    tok=os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]
    sep="&" if "?" in url else "?"
    req=urllib.request.Request(url+sep+"audience=arbm-sist-benchmark",headers={"Authorization":"Bearer "+tok})
    with urllib.request.urlopen(req,timeout=20) as r: return json.loads(r.read())["value"]
def main():
    token=oidc(); body=json.dumps({"mode":"inventory"}).encode()
    req=urllib.request.Request(API,data=body,method="POST",headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=20) as r: data=json.loads(r.read())
    print(json.dumps(data,separators=(",",":")))
    return 0 if data.get("status")=="PASS" and data.get("values_exposed") is False else 2
if __name__=="__main__": raise SystemExit(main())
