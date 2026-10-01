from __future__ import annotations
from odf.opendocument import load
from odf.table import Table, TableRow, TableCell
from odf import teletype
import re

PT_FUNCS={"SOMA":"SUM","MÉDIA":"AVERAGE","MEDIA":"AVERAGE","MÍN":"MIN","MÁX":"MAX"}

def _a(n,k):
    try:return n.getAttribute(k)
    except:return None

def normalize_number(v):
    if isinstance(v,(int,float)): return float(v)
    if v is None:return None
    s=str(v).strip()
    if re.match(r"^-?\d{1,3}(\.\d{3})*,\d+$",s): s=s.replace(".","").replace(",",".")
    else:s=s.replace(",",".")
    try:return float(s)
    except:return v

def normalize_formula(s):
    if s is None:return None
    x=str(s).strip()
    x=re.sub(r"^of:=","=",x,flags=re.I)
    x=x.replace("[.","").replace("]","").replace(":. ",":").replace(":.",":")
    x=x.replace("; ",",").replace(";",",")
    for pt,en in PT_FUNCS.items(): x=re.sub(rf"\b{re.escape(pt)}\b",en,x,flags=re.I)
    return re.sub(r"\s+","",x).upper()

def read_book(path):
    doc=load(str(path)); out=[]
    for sh in doc.spreadsheet.getElementsByType(Table):
        rows=[]
        for r in sh.childNodes:
            if getattr(r,"qname",None)!=TableRow().qname:continue
            cells=[]
            for c in r.childNodes:
                if getattr(c,"qname",None)==TableCell().qname:
                    cells.append({"text":teletype.extractText(c),"value":_a(c,"value"),"formula":_a(c,"formula")})
            rows.append(cells)
        out.append({"name":_a(sh,"name"),"rows":rows})
    return out

def _sheet(book,name):
    return next((s for s in book if s["name"]==name),None)

def cell(book,sheet,row,col):
    s=_sheet(book,sheet)
    if not s or row<1 or col<1 or row>len(s["rows"]) or col>len(s["rows"][row-1]): return None
    return s["rows"][row-1][col-1]

def verify(path,spec):
    b=read_book(path); t=spec["type"]; p=spec["params"]
    if t=="sheet_exists": return _sheet(b,p["sheet"]) is not None
    if t=="sheet_not_exists": return _sheet(b,p["sheet"]) is None
    if t=="sheet_count": return len(b)==p["expected"]
    if t=="sheet_order": return [s["name"] for s in b]==p["expected"]
    if t=="cell_text":
        c=cell(b,p["sheet"],p["row"],p["col"]); return bool(c) and c["text"]==str(p["expected"])
    if t=="cell_value":
        c=cell(b,p["sheet"],p["row"],p["col"])
        if not c:return False
        actual=normalize_number(c["value"] if c["value"] is not None else c["text"])
        return actual==normalize_number(p["expected"])
    if t=="formula_in_cell":
        c=cell(b,p["sheet"],p["row"],p["col"]); return bool(c) and normalize_formula(c["formula"])==normalize_formula(p["expected"])
    if t in ("row_exists","row_not_exists"):
        s=_sheet(b,p["sheet"])
        found=bool(s) and any(len(r)>=p["col"] and r[p["col"]-1]["text"]==str(p["value"]) for r in s["rows"])
        return found if t=="row_exists" else not found
    if t=="cell_value_by_row_label":
        s=_sheet(b,p["sheet"])
        if not s:return False
        for r in s["rows"]:
            if len(r)>=p["label_col"] and r[p["label_col"]-1]["text"]==str(p["label"]):
                if len(r)<p["target_col"]:return False
                c=r[p["target_col"]-1]
                actual=normalize_number(c["value"] if c["value"] is not None else c["text"])
                return actual==normalize_number(p["expected"])
        return False
    if t=="row_count":
        s=_sheet(b,p["sheet"]); return bool(s) and len(s["rows"])==p["expected"]
    if t=="row_matches":
        s=_sheet(b,p["sheet"])
        if not s:return False
        expected=[str(x) for x in p["expected"]]
        return any([c["text"] for c in r[:len(expected)]]==expected for r in s["rows"])
    if t in ("column_exists","column_not_exists"):
        s=_sheet(b,p["sheet"])
        found=False if not s else any(len(r)>=p["col"] for r in s["rows"])
        return found if t=="column_exists" else not found
    if t=="column_values":
        s=_sheet(b,p["sheet"])
        if not s:return False
        vals=[r[p["col"]-1]["text"] for r in s["rows"] if len(r)>=p["col"]]
        return vals==[str(x) for x in p["expected"]]
    if t=="formula_result":
        c=cell(b,p["sheet"],p["row"],p["col"])
        if not c:return False
        actual=normalize_number(c["value"] if c["value"] is not None else c["text"])
        return actual==normalize_number(p["expected"])
    if t=="sheet_renamed":
        return _sheet(b,p["old"]) is None and _sheet(b,p["new"]) is not None
    if t in ("range_sorted_ascending","range_sorted_descending"):
        s=_sheet(b,p["sheet"])
        if not s:return False
        vals=[]
        for r in s["rows"][p.get("start_row",1)-1:p.get("end_row",len(s["rows"]))]:
            if len(r)>=p["col"]:
                v=r[p["col"]-1]["value"] if r[p["col"]-1]["value"] is not None else r[p["col"]-1]["text"]
                vals.append(normalize_number(v))
        target=sorted(vals, reverse=(t=="range_sorted_descending"))
        return vals==target
    if t=="column_order":
        s=_sheet(b,p["sheet"])
        return bool(s and s["rows"]) and [c["text"] for c in s["rows"][0][:len(p["expected"])]]==[str(x) for x in p["expected"]]
    if t=="formula_pattern":
        c=cell(b,p["sheet"],p["row"],p["col"])
        return bool(c) and re.search(p["pattern"],normalize_formula(c["formula"]) or "") is not None
    if t in ("row_inserted","row_deleted"):
        alias={"type":"row_exists" if t=="row_inserted" else "row_not_exists","params":p}
        return verify(path,alias)
    if t in ("column_inserted","column_deleted"):
        alias={"type":"column_exists" if t=="column_inserted" else "column_not_exists","params":p}
        return verify(path,alias)
    if t in ("range_copied","range_moved"):
        s=_sheet(b,p["sheet"])
        if not s:return False
        def rv(start_row,start_col,rows,cols):
            out=[]
            for rr in range(start_row,start_row+rows):
                row=[]
                for cc in range(start_col,start_col+cols):
                    c=cell(b,p["sheet"],rr,cc); row.append(None if c is None else c["text"])
                out.append(row)
            return out
        target=rv(p["target_row"],p["target_col"],p["rows"],p["cols"])
        if target!=p["expected"]:return False
        if t=="range_moved" and p.get("source_cleared"):
            src=rv(p["source_row"],p["source_col"],p["rows"],p["cols"])
            return all(v in (None,"") for row in src for v in row)
        return True
    if t in ("filter_active","filter_condition","visible_rows_match"):
        from odf.table import FilterCondition
        doc=load(str(path)); conds=doc.spreadsheet.getElementsByType(FilterCondition)
        if t=="filter_active": return len(conds)>0
        if not conds:return False
        if t=="filter_condition":
            return any(_a(c,"fieldnumber")==str(p["field_number"]) and _a(c,"operator")==p["operator"] and _a(c,"value")==str(p["value"]) for c in conds)
        s=_sheet(b,p["sheet"])
        if not s:return False
        field=p["field_number"]+1; op=p["operator"]; val=str(p["value"]); key_col=p.get("key_col",1)
        matches=[]
        for r in s["rows"][p.get("start_row",2)-1:]:
            if len(r)<max(field,key_col):continue
            actual=r[field-1]["text"]
            ok=(actual==val) if op=="=" else (actual!=val if op=="!=" else False)
            if ok:matches.append(r[key_col-1]["text"])
        return matches==[str(x) for x in p["expected_keys"]]
    raise ValueError(t)
