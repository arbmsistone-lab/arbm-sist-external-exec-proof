from __future__ import annotations
import re, zipfile
from pathlib import Path
from datetime import datetime, timezone

def rewrite_members(path, replacements):
    path=Path(path); tmp=Path(str(path)+".rewrite")
    with zipfile.ZipFile(path,"r") as src, zipfile.ZipFile(tmp,"w") as dst:
        for info in src.infolist():
            data=replacements.get(info.filename,src.read(info.filename))
            zi=zipfile.ZipInfo(info.filename,info.date_time)
            zi.external_attr=info.external_attr
            zi.compress_type=zipfile.ZIP_STORED if info.filename=="mimetype" else zipfile.ZIP_DEFLATED
            dst.writestr(zi,data)
    tmp.replace(path)

def add_ignored_noise(path):
    with zipfile.ZipFile(path,"r") as z:
        meta=z.read("meta.xml").decode("utf-8","replace")
        settings=z.read("settings.xml").decode("utf-8","replace") if "settings.xml" in z.namelist() else None
    now=datetime.now(timezone.utc).isoformat()
    meta=re.sub(r"<dc:date>.*?</dc:date>",f"<dc:date>{now}</dc:date>",meta,flags=re.S)
    if "<dc:creator>" in meta:
        meta=re.sub(r"<dc:creator>.*?</dc:creator>","<dc:creator>M1_METADATA_NOISE</dc:creator>",meta,flags=re.S)
    else:
        meta=meta.replace("</office:meta>","<dc:creator>M1_METADATA_NOISE</dc:creator></office:meta>")
    repl={"meta.xml":meta.encode("utf-8")}
    if settings is not None:
        settings=settings.replace("</office:settings>","<config:config-item-set config:name=\"M1ViewNoise\"><config:config-item config:name=\"ActiveCell\" config:type=\"string\">B2</config:config-item><config:config-item config:name=\"ViewPosition\" config:type=\"int\">777</config:config-item></config:config-item-set></office:settings>")
        repl["settings.xml"]=settings.encode("utf-8")
    rewrite_members(path,repl)
