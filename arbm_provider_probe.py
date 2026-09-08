import json, os, urllib.request, urllib.error
API_URL="https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-terminal-agent-v3"
MODELS=["gemini-3.8-flash","gemini-3.7-flash","gemini-3.6-flash","gemini-3.5-flash","gemini-3.5-flash-lite","gemini-3.1-flash-lite","gemini-2.5-flash","gemini-2.5-flash-lite"]
def oidc():
 url=os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]; token=os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]
 sep="&" if "?" in url else "?"; req=urllib.request.Request(url+sep+"audience=arbm-sist-benchmark",headers={"Authorization":"Bearer "+token})
 with urllib.request.urlopen(req,timeout=20) as r:return json.loads(r.read().decode())["value"]
def probe(model,token):
 body={"instruction":"Return one safe first shell command as JSON.","observation":"No commands executed yet.","step":1,"provider_hint":"google","model_hint":model}
 req=urllib.request.Request(API_URL,data=json.dumps(body).encode(),method="POST",headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"})
 try:
  with urllib.request.urlopen(req,timeout=40) as r:data=json.loads(r.read().decode()); return {"model":model,"http":r.status,"ok":data.get("ok"),"provider":data.get("provider"),"mandatory_cost_usd":data.get("mandatory_cost_usd"),"paid_fallback_used":data.get("paid_fallback_used"),"attempts":data.get("provider_attempts",[])}
 except urllib.error.HTTPError as e:
  data=json.loads(e.read().decode()); return {"model":model,"http":e.code,"ok":False,"status":data.get("status"),"attempts":data.get("provider_attempts",[])}
def main():
 token=oidc(); rows=[probe(m,token) for m in MODELS]; print(json.dumps(rows,separators=(",",":")))
 good=[r for r in rows if r.get("http")==200 and r.get("ok") is True and r.get("mandatory_cost_usd")==0 and r.get("paid_fallback_used") is False]
 print(json.dumps({"models_tested":len(rows),"free_models_live":len(good),"live_models":[r["model"] for r in good],"mandatory_cost_usd":0},separators=(",",":")))
 if len(good)<2: raise SystemExit(2)
if __name__=="__main__":main()