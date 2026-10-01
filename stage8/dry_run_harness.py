from __future__ import annotations
from pathlib import Path
import json,subprocess,sys,time

ROOT=Path(__file__).resolve().parent.parent

def run_adapter(adapter_cmd, task_file, output_dir):
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    started=time.monotonic()
    p=subprocess.run(adapter_cmd+[str(task_file)],capture_output=True,text=True,timeout=30)
    result={
      "returncode":p.returncode,
      "stdout":p.stdout,
      "stderr":p.stderr,
      "elapsed_seconds":time.monotonic()-started
    }
    (out/"result.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    return result

if __name__=="__main__":
    print("DRY_RUN_HARNESS_READY")
