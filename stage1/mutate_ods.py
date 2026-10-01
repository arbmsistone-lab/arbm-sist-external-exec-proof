from __future__ import annotations
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

NS={"office":"urn:oasis:names:tc:opendocument:xmlns:office:1.0",
"table":"urn:oasis:names:tc:opendocument:xmlns:table:1.0",
"text":"urn:oasis:names:tc:opendocument:xmlns:text:1.0",
"dc":"http://purl.org/dc/elements/1.1/",
"meta":"urn:oasis:names:tc:opendocument:xmlns:meta:1.0",
"config":"urn:oasis:names:tc:opendocument:xmlns:config:1.0"}
for k,v in NS.items(): ET.register_namespace(k,v)

def read_zip(path):
    with zipfile.ZipFile(path,"r") as z:
        infos=z.infolist(); data={i.filename:z.read(i.filename) for i in infos}
    return infos,data

def write_zip(path,infos,data):
    path=Path(path); tmp=Path(str(path)+".tmp")
    with zipfile.ZipFile(tmp,"w") as z:
        if "mimetype" in data:
            zi=zipfile.ZipInfo("mimetype"); zi.compress_type=zipfile.ZIP_STORED; z.writestr(zi,data["mimetype"])
        for i in infos:
            if i.filename=="mimetype": continue
            zi=zipfile.ZipInfo(i.filename); zi.compress_type=zipfile.ZIP_DEFLATED; zi.date_time=i.date_time; zi.external_attr=i.external_attr
            z.writestr(zi,data[i.filename])
    tmp.replace(path)

def roots(content):
    root=ET.fromstring(content); ss=root.find(".//office:body/office:spreadsheet",NS)
    if ss is None: raise RuntimeError("spreadsheet ausente")
    sh=ss.find("table:table",NS)
    if sh is None: raise RuntimeError("aba ausente")
    return root,ss,sh

def set_string(cell,text):
    for ch in list(cell): cell.remove(ch)
    for a in [f"{{{NS['office']}}}value",f"{{{NS['office']}}}date-value",f"{{{NS['office']}}}boolean-value"]:
        cell.attrib.pop(a,None)
    cell.set(f"{{{NS['office']}}}value-type","string")
    p=ET.SubElement(cell,f"{{{NS['text']}}}p"); p.text=text

def mutate_semantic(path,run):
    path=Path(path); infos,data=read_zip(path); root,ss,sh=roots(data["content.xml"])
    mode=(run-1)%6
    cells=sh.findall(".//table:table-cell",NS)
    rows=sh.findall("table:table-row",NS)
    if mode==0:
        set_string(cells[0],f"MUT_VALUE_{run}"); kind="CELL_VALUE"
    elif mode==1:
        set_string(cells[1 if len(cells)>1 else 0],f"MUT_TEXT_{run}"); kind="CELL_TEXT"
    elif mode==2:
        row=ET.SubElement(sh,f"{{{NS['table']}}}table-row")
        c=ET.SubElement(row,f"{{{NS['table']}}}table-cell"); set_string(c,f"NEW_ROW_{run}"); kind="ROW_INSERT"
    elif mode==3:
        if len(rows)<2: raise RuntimeError("fixture precisa de ao menos 2 linhas")
        sh.remove(rows[-1]); kind="ROW_DELETE"
    elif mode==4:
        nsh=ET.SubElement(ss,f"{{{NS['table']}}}table"); nsh.set(f"{{{NS['table']}}}name",f"MutationSheet{run}")
        row=ET.SubElement(nsh,f"{{{NS['table']}}}table-row"); c=ET.SubElement(row,f"{{{NS['table']}}}table-cell"); set_string(c,"created")
        kind="SHEET_CREATE"
    else:
        old=sh.get(f"{{{NS['table']}}}name","Sheet1"); sh.set(f"{{{NS['table']}}}name",f"{old}_MUT_{run}"); kind="SHEET_RENAME"
    data["content.xml"]=ET.tostring(root,encoding="utf-8",xml_declaration=True); write_zip(path,infos,data); return kind
