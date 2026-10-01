from __future__ import annotations
import argparse, shutil
from pathlib import Path
from semantic_hash import semantic_hash

def reset_fixture(source:str|Path,dest:str|Path)->str:
    src=Path(source).resolve(); dst=Path(dest).resolve()
    if not src.exists(): raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(src,dst)
    hs,hd=semantic_hash(src),semantic_hash(dst)
    if hs!=hd: raise RuntimeError("reset produziu hash semântico diferente")
    return hd

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--source",required=True); ap.add_argument("--dest",required=True)
    a=ap.parse_args()
    print("RESET_OK"); print("SEMANTIC_SHA256="+reset_fixture(a.source,a.dest))