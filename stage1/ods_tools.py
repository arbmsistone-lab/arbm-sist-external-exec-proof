from __future__ import annotations
import hashlib, json, shutil
from pathlib import Path
from odf.opendocument import load
from odf.table import Table, TableRow, TableCell
from odf.text import P
from odf import teletype

def _attr(node, name):
    try:
        return node.getAttribute(name)
    except Exception:
        return None

def _cell_state(cell):
    return {
        "type": _attr(cell, "valuetype"),
        "value": _attr(cell, "value"),
        "formula": _attr(cell, "formula"),
        "text": teletype.extractText(cell),
        "repeat": _attr(cell, "numbercolumnsrepeated") or "1",
    }

def semantic_state(path):
    doc=load(str(path))
    out=[]
    for sheet in doc.spreadsheet.getElementsByType(Table):
        rows=[]
        for row in sheet.childNodes:
            if getattr(row,"qname",None) != TableRow().qname:
                continue
            cells=[]
            for cell in row.childNodes:
                if getattr(cell,"qname",None) == TableCell().qname:
                    cells.append(_cell_state(cell))
            rows.append(cells)
        out.append({"sheet":_attr(sheet,"name"),"rows":rows})
    return out

def semantic_hash(path):
    raw=json.dumps(semantic_state(path),ensure_ascii=False,separators=(",",":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def reset_fixture(source,dest):
    source=Path(source); dest=Path(dest)
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,dest)
    if semantic_hash(source)!=semantic_hash(dest):
        raise RuntimeError("RESET_HASH_MISMATCH")
    return semantic_hash(dest)

def _first_sheet(doc):
    sheets=doc.spreadsheet.getElementsByType(Table)
    if not sheets: raise RuntimeError("NO_SHEET")
    return sheets[0]

def _direct_rows(sheet):
    return [n for n in sheet.childNodes if getattr(n,"qname",None)==TableRow().qname]

def _direct_cells(row):
    return [n for n in row.childNodes if getattr(n,"qname",None)==TableCell().qname]

def _set_string(cell,text):
    for ch in list(cell.childNodes): cell.removeChild(ch)
    for k in ("value","datevalue","booleanvalue","formula"):
        try: cell.removeAttribute(k)
        except Exception: pass
    cell.setAttribute("valuetype","string")
    cell.addElement(P(text=text))

def mutate_semantic(path,run_index):
    doc=load(str(path)); sheet=_first_sheet(doc)
    rows=_direct_rows(sheet)
    if len(rows)<2: raise RuntimeError("NEED_2_ROWS")
    mode=(run_index-1)%6
    if mode==0:
        _set_string(_direct_cells(rows[0])[0],f"MUT_VALUE_{run_index}"); kind="CELL_VALUE"
    elif mode==1:
        _set_string(_direct_cells(rows[0])[1],f"MUT_TEXT_{run_index}"); kind="CELL_TEXT"
    elif mode==2:
        row=TableRow(); c=TableCell(valuetype="string"); c.addElement(P(text=f"NEW_ROW_{run_index}")); row.addElement(c); sheet.addElement(row); kind="ROW_INSERT"
    elif mode==3:
        sheet.removeChild(rows[-1]); kind="ROW_DELETE"
    elif mode==4:
        ns=Table(name=f"MutationSheet{run_index}"); r=TableRow(); c=TableCell(valuetype="string"); c.addElement(P(text="created")); r.addElement(c); ns.addElement(r); doc.spreadsheet.addElement(ns); kind="SHEET_CREATE"
    else:
        sheet.setAttribute("name",f"{_attr(sheet,'name')}_MUT_{run_index}"); kind="SHEET_RENAME"
    doc.save(str(path),addsuffix=False)
    return kind

def set_numeric_or_text_10(path,numeric):
    doc=load(str(path)); sheet=_first_sheet(doc); rows=_direct_rows(sheet); cells=_direct_cells(rows[1])
    c=cells[1]
    for ch in list(c.childNodes): c.removeChild(ch)
    for k in ("value","formula"):
        try: c.removeAttribute(k)
        except Exception: pass
    if numeric:
        c.setAttribute("valuetype","float"); c.setAttribute("value","10")
    else:
        c.setAttribute("valuetype","string")
    c.addElement(P(text="10"))
    doc.save(str(path),addsuffix=False)
