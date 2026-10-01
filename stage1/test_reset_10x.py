from __future__ import annotations
import argparse, shutil
from pathlib import Path
from ods_tools import semantic_hash, reset_fixture, mutate_semantic, set_numeric_or_text_10
from metadata_noise import add_ignored_noise

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",required=True)
    ap.add_argument("--dest",required=True)
    ap.add_argument("--runs",type=int,default=10)
    a=ap.parse_args()
    src=Path(a.source).resolve(); dst=Path(a.dest).resolve()
    if not src.exists(): raise SystemExit(f"ERRO: fixture ausente: {src}")
    original=semantic_hash(src)
    detected=0; restored=0

    for i in range(1,a.runs+1):
        reset_fixture(src,dst)
        kind=mutate_semantic(dst,i)
        changed=semantic_hash(dst)!=original
        if changed: detected+=1
        reset_fixture(src,dst)
        reset_ok=semantic_hash(dst)==original
        if reset_ok: restored+=1
        print(f"RUN {i:02d}/{a.runs}: MUTATION={kind} DETECTED={'PASS' if changed else 'FAIL'} RESET={'PASS' if reset_ok else 'FAIL'}")

    print(f"MUTATION_DETECTED_{detected}/{a.runs}")
    print(f"RESET_RESTORED_{restored}/{a.runs}")

    meta=dst.with_name("m1_metadata_view_noise.ods")
    shutil.copy2(src,meta)
    before=semantic_hash(meta)
    add_ignored_noise(meta)
    meta_ok=semantic_hash(meta)==before
    print(f"METADATA_IGNORED={'PASS' if meta_ok else 'FAIL'}")

    nfile=dst.with_name("m1_numeric_10.ods")
    tfile=dst.with_name("m1_text_10.ods")
    shutil.copy2(src,nfile); shutil.copy2(src,tfile)
    set_numeric_or_text_10(nfile,True); set_numeric_or_text_10(tfile,False)
    type_ok=semantic_hash(nfile)!=semantic_hash(tfile)
    print(f"NUMERIC_TYPE_DISTINGUISHED={'PASS' if type_ok else 'FAIL'}")

    for f in (meta,nfile,tfile):
        try: f.unlink()
        except FileNotFoundError: pass

    ok=(detected==a.runs and restored==a.runs and meta_ok and type_ok)
    raise SystemExit(0 if ok else 1)

if __name__=="__main__":
    main()
