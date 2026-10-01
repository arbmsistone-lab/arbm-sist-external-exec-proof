from __future__ import annotations
import hashlib, zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

SEMANTIC_MEMBERS=("content.xml","styles.xml","mimetype")

def canonical_xml(data:bytes)->bytes:
    root=ET.fromstring(data)
    def clean(e):
        if e.text is not None and e.text.strip()=="": e.text=None
        if e.tail is not None and e.tail.strip()=="": e.tail=None
        for c in e: clean(c)
    clean(root)
    return ET.tostring(root,encoding="utf-8",method="xml")

def semantic_hash(path:str|Path)->str:
    path=Path(path)
    if not path.exists(): raise FileNotFoundError(path)
    if path.suffix.lower()!=".ods": raise ValueError(f"Esperado .ods: {path}")
    h=hashlib.sha256()
    with zipfile.ZipFile(path,"r") as z:
        names=set(z.namelist())
        for member in SEMANTIC_MEMBERS:
            if member not in names: raise RuntimeError(f"ODS inválido: {member} ausente")
            data=z.read(member)
            if member.endswith(".xml"): data=canonical_xml(data)
            h.update(member.encode()+b"\0"+data+b"\0")
    return h.hexdigest()