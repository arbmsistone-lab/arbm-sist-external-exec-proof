from __future__ import annotations
from pathlib import Path
import json, zipfile
from odf.opendocument import load
from odf.table import Table,TableRow,TableCell
from odf import teletype

def _a(n,k):
    try:return n.getAttribute(k)
    except:return None

def semantic_state(path):
    doc=load(str(path)); sheets=[]
    for sh in doc.spreadsheet.getElementsByType(Table):
        rows=[]
        for r in sh.childNodes:
            if getattr(r,"qname",None)!=TableRow().qname: continue
            cells=[]
            for c in r.childNodes:
                if getattr(c,"qname",None)!=TableCell().qname: continue
                cells.append({
                    "text":teletype.extractText(c),
                    "type":_a(c,"valuetype"),
                    "value":_a(c,"value"),
                    "formula":_a(c,"formula"),
                    "style":_a(c,"stylename"),
                    "repeat":_a(c,"numbercolumnsrepeated") or "1",
                })
            rows.append(cells)
        sheets.append({"name":_a(sh,"name"),"rows":rows})
    return sheets

def is_valid_ods(path):
    p=Path(path)
    if not p.exists() or not zipfile.is_zipfile(p): return False
    try:
        with zipfile.ZipFile(p) as z:
            return z.read("mimetype").decode("ascii","strict")=="application/vnd.oasis.opendocument.spreadsheet"
    except Exception:
        return False

def first_diff(a,b,path="$"):
    if type(a)!=type(b): return f"{path}:TYPE"
    if isinstance(a,dict):
        if set(a)!=set(b): return f"{path}:KEYS"
        for k in sorted(a):
            d=first_diff(a[k],b[k],f"{path}.{k}")
            if d:return d
    elif isinstance(a,list):
        if len(a)!=len(b): return f"{path}:LEN {len(a)}!={len(b)}"
        for i,(x,y) in enumerate(zip(a,b)):
            d=first_diff(x,y,f"{path}[{i}]")
            if d:return d
    elif a!=b:return f"{path}:{a!r}!={b!r}"
    return None

def check_integrity(*,final_path,expected_semantic_path,target_verifier_pass,expected_output_path):
    result={
      "TARGET_VERIFIER":"PASS" if target_verifier_pass else "FAIL",
      "UNEXPECTED_MUTATIONS":None,
      "OUTPUT_PATH":"PASS",
      "OUTPUT_FORMAT":"PASS",
      "FIRST_UNEXPECTED_DIFF":None,
      "PASS":False,
    }
    final=Path(final_path); expected=Path(expected_semantic_path)
    if final.resolve()!=Path(expected_output_path).resolve(): result["OUTPUT_PATH"]="FAIL"
    if not is_valid_ods(final): result["OUTPUT_FORMAT"]="FAIL"
    if result["OUTPUT_FORMAT"]=="PASS":
        d=first_diff(semantic_state(final),semantic_state(expected))
        result["FIRST_UNEXPECTED_DIFF"]=d
        result["UNEXPECTED_MUTATIONS"]=0 if d is None else 1
    else:
        result["UNEXPECTED_MUTATIONS"]=1
    result["PASS"]=(target_verifier_pass and result["UNEXPECTED_MUTATIONS"]==0 and result["OUTPUT_PATH"]=="PASS" and result["OUTPUT_FORMAT"]=="PASS")
    return result
