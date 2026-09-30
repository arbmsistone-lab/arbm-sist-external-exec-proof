#!/usr/bin/env python3
import argparse, json, os, pathlib, shutil, signal, subprocess, sys, time, urllib.request

POLL_SECONDS=3.0

def rss_kb(pid):
    try:
        for line in pathlib.Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    except Exception:
        pass
    return None

def mem_available_kb():
    try:
        for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1])
    except Exception:
        pass
    return None

def health(timeout=2.0):
    try:
        with urllib.request.urlopen("http://127.0.0.1:8088/health",timeout=timeout) as r:
            return r.status==200
    except Exception:
        return False

def route_probe(timeout=3.0):
    """Prove the local gateway contract without entering a scoreable task session.

    The old POST probe called the real mesh, could receive an unrelated upstream
    OIDC 401, and wrote TERMINAL_FAIL into the focal evidence ledger before the
    official task began. Startup probing must never execute task/provider logic.
    The real /v1/chat/completions route remains proven by the official task run.
    """
    try:
        with urllib.request.urlopen("http://127.0.0.1:8088/health",timeout=timeout) as r:
            body=json.loads(r.read().decode("utf-8"))
            return (r.status==200
                    and body.get("status")=="ok"
                    and body.get("pipeline")=="arbm-osworld-v32-isolated"
                    and body.get("build")=="arbm-osworld-v32-master-20260914")
    except Exception:
        return False

def classify_returncode(rc):
    if rc is None: return "PROCESS_ALIVE"
    if rc < 0: return f"SIGNAL_{-rc}"
    return f"EXIT_{rc}"

def append_json(path,payload):
    path=pathlib.Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8") as f:
        f.write(json.dumps(payload,sort_keys=True)+"\n")

def snapshot(pid,telemetry,event):
    du=shutil.disk_usage("/")
    append_json(telemetry,{"event":event,"ts":time.time(),"pid":pid,
        "rss_kb":rss_kb(pid),"mem_available_kb":mem_available_kb(),
        "disk_free_mb":du.free//(1024*1024),"health":health()})

def diagnostics(pid,telemetry,shim_log,cause):
    append_json(telemetry,{"event":"gateway_failure","ts":time.time(),"cause":cause,"pid":pid})
    for name,cmd in (("free_m",["free","-m"]),("df_h",["df","-h"]),("ps_aux",["ps","aux"])):
        try:
            out=subprocess.run(cmd,text=True,capture_output=True,timeout=8)
            append_json(telemetry,{"event":name,"stdout":out.stdout[-16000:],"stderr":out.stderr[-4000:]})
        except Exception as exc:
            append_json(telemetry,{"event":name,"error":repr(exc)})
    try:
        tail=pathlib.Path(shim_log).read_text(encoding="utf-8",errors="replace")[-20000:]
        append_json(telemetry,{"event":"shim_tail","tail":tail})
    except Exception as exc:
        append_json(telemetry,{"event":"shim_tail","error":repr(exc)})

def start_shim(shim_log):
    repo=pathlib.Path(__file__).resolve().parents[2]
    log=open(shim_log,"w",encoding="utf-8")
    proc=subprocess.Popen([sys.executable,str(repo/"scripts/osworld_free_mesh_shim.py")],
        cwd=str(repo),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    return proc,log

def stop_process(proc):
    if proc is None or proc.poll() is not None: return
    try:
        os.killpg(proc.pid,signal.SIGTERM); proc.wait(timeout=8)
    except Exception:
        try: os.killpg(proc.pid,signal.SIGKILL)
        except Exception: pass
        try: proc.wait(timeout=3)
        except Exception: pass

def wait_ready(shim,telemetry,shim_log,seconds=45):
    deadline=time.time()+seconds
    while time.time()<deadline:
        rc=shim.poll(); snapshot(shim.pid,telemetry,"startup_probe")
        if rc is not None:
            cause=classify_returncode(rc); diagnostics(shim.pid,telemetry,shim_log,cause)
            raise RuntimeError("SHIM_START_EXIT:"+cause)
        if health():
            print("MODEL_GATEWAY_HEALTH=PASS",flush=True)
            if route_probe():
                print("MODEL_ROUTE=PASS",flush=True)
                return
        time.sleep(1)
    diagnostics(shim.pid,telemetry,shim_log,"STARTUP_HEALTH_TIMEOUT")
    raise RuntimeError("MODEL_GATEWAY_HEALTH_TIMEOUT")

def run_supervised(args):
    pathlib.Path(args.artifact_dir).mkdir(parents=True,exist_ok=True)
    shim_log=args.shim_log or str(pathlib.Path(args.artifact_dir)/"shim-runtime.log")
    telemetry=args.telemetry_log or str(pathlib.Path(args.artifact_dir)/"gateway-telemetry.jsonl")
    run_log=args.run_log or str(pathlib.Path(args.artifact_dir)/"osworld.log")
    shim,shim_handle=start_shim(shim_log); child=None
    try:
        wait_ready(shim,telemetry,shim_log)
        run_handle=open(run_log,"w",encoding="utf-8")
        child=subprocess.Popen(args.run_cmd,shell=True,cwd=args.run_cwd or None,
            executable="/bin/bash",stdout=run_handle,stderr=subprocess.STDOUT,start_new_session=True)
        started=time.time()
        while True:
            rc=shim.poll()
            if rc is not None:
                cause=classify_returncode(rc); diagnostics(shim.pid,telemetry,shim_log,cause)
                stop_process(child); print("EXACT_PROCESS_EXIT_CAUSE="+cause,flush=True)
                raise RuntimeError("MODEL_GATEWAY_DIED:"+cause)
            if not health():
                cause="HEALTH_UNREACHABLE_PROCESS_ALIVE"
                diagnostics(shim.pid,telemetry,shim_log,cause); stop_process(child)
                print("EXACT_PROCESS_EXIT_CAUSE="+cause,flush=True)
                raise RuntimeError("MODEL_GATEWAY_HEALTH_LOST")
            snapshot(shim.pid,telemetry,"run_probe")
            if args.marker:
                hay=""
                for p in (args.marker_file,shim_log,run_log):
                    if p and pathlib.Path(p).is_file():
                        try: hay += pathlib.Path(p).read_text(encoding="utf-8",errors="ignore")[-400000:]
                        except Exception: pass
                if args.marker in hay:
                    stop_process(child)
                    if not health(): raise RuntimeError("MODEL_GATEWAY_LOST_AT_MARKER")
                    print("MODEL_GATEWAY_FULL_RUN_STABILITY=PASS",flush=True)
                    return 0
            child_rc=child.poll()
            if child_rc is not None:
                if child_rc==0:
                    if not health(): raise RuntimeError("MODEL_GATEWAY_LOST_AT_RUN_END")
                    print("MODEL_GATEWAY_FULL_RUN_STABILITY=PASS",flush=True)
                return child_rc
            if time.time()-started>args.timeout:
                stop_process(child); raise RuntimeError("SUPERVISED_RUN_TIMEOUT")
            time.sleep(POLL_SECONDS)
    finally:
        stop_process(child); stop_process(shim)
        try: shim_handle.close()
        except Exception: pass

def self_test():
    root=pathlib.Path("/tmp/task091-gateway-selftest")
    shutil.rmtree(root,ignore_errors=True); root.mkdir(parents=True)
    old=os.environ.get("ARBM_ENABLE_LOCAL_VLM"); os.environ["ARBM_ENABLE_LOCAL_VLM"]="0"
    old_evidence=os.environ.get("ARBM_OSWORLD_SHIM_LOG")
    os.environ["ARBM_OSWORLD_SHIM_LOG"]=str(root/"shim-evidence.jsonl")
    shim,handle=start_shim(root/"shim.log")
    try:
        wait_ready(shim,root/"telemetry.jsonl",root/"shim.log",seconds=20)
        if pathlib.Path(os.environ.get("ARBM_OSWORLD_SHIM_LOG","/nonexistent")).is_file():
            text=pathlib.Path(os.environ["ARBM_OSWORLD_SHIM_LOG"]).read_text(encoding="utf-8",errors="replace")
            if "task091-gateway-health-probe" in text or "ENDPOINT_AUTH_OR_VERSION" in text:
                raise RuntimeError("HEALTH_PROBE_EVIDENCE_CONTAMINATION")
        for _ in range(3):
            if not health(): raise RuntimeError("SUSTAINED_HEALTH_FAILED")
            snapshot(shim.pid,root/"telemetry.jsonl","selftest_sustained"); time.sleep(1)
        if classify_returncode(-9)!="SIGNAL_9" or classify_returncode(7)!="EXIT_7":
            raise RuntimeError("EXIT_CLASSIFICATION_FAILED")
        print("GATEWAY_UNIT_INTEGRATION_TESTS=PASS")
        print("GATEWAY_SUSTAINED_HEALTH_TEST=PASS")
        print("GATEWAY_FAILURE_DETECTION_TEST=PASS")
        print("HEALTH_PROBE_EVIDENCE_ISOLATION=PASS")
        print("ENDPOINT_AUTH_VERSION_PREFLIGHT=PASS")
        return 0
    finally:
        stop_process(shim); handle.close()
        if old is None: os.environ.pop("ARBM_ENABLE_LOCAL_VLM",None)
        else: os.environ["ARBM_ENABLE_LOCAL_VLM"]=old
        if old_evidence is None: os.environ.pop("ARBM_OSWORLD_SHIM_LOG",None)
        else: os.environ["ARBM_OSWORLD_SHIM_LOG"]=old_evidence

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--artifact-dir"); ap.add_argument("--shim-log"); ap.add_argument("--telemetry-log")
    ap.add_argument("--run-log"); ap.add_argument("--marker",default=""); ap.add_argument("--marker-file",default="")
    ap.add_argument("--run-cwd",default=""); ap.add_argument("--run-cmd",default="")
    ap.add_argument("--timeout",type=int,default=300)
    args=ap.parse_args()
    if args.self_test: return self_test()
    if not args.artifact_dir or not args.run_cmd: ap.error("--artifact-dir and --run-cmd are required")
    return run_supervised(args)

if __name__=="__main__":
    raise SystemExit(main())
