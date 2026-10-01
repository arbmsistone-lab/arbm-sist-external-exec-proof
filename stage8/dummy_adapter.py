from __future__ import annotations
import json,sys
task=sys.argv[1]
print(json.dumps({"adapter":"DUMMY","task":task,"claim":"SUCCESS","model_calls":0,"paid_cost_usd":0.0}))
