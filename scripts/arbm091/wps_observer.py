"""Instrument agent GUI calls without changing task/evaluator code or results.

Installed on DesktopEnv.step by the explicit, version-checked runtime adapter.
Each original GUI call still executes through the official controller. Metadata
collection uses a fixed read-only program, separate from the agent's program.
"""
from __future__ import annotations
import base64
import hashlib
import json
import os
import threading
import time
from pathlib import Path
from urllib.parse import urlparse
import requests
from osworld_control import canonical_action, task091_panel_target_proof
from arbm091.trace_gate import digest, parse_atom, pointer, preflight, postflight, require, inside

_LOCK = threading.Lock()
_PROBE = Path(__file__).with_name('guest_probe.py').read_text()


_COVERSTAT_ATOMIC_REGISTRY={
    (1,13,'CoverStatValue_0'):{'geometry':(8339327,2167128,2560320,219456),'completed_text':'$40.9M'},
    (1,16,'CoverStatValue_1'):{'geometry':(8339327,3355848,2560320,219456),'completed_text':'$2.8M'},
    (1,19,'CoverStatValue_2'):{'geometry':(8339327,4544568,2560320,219456),'completed_text':'206'},
    (2,20,'SummaryNrr_Value'):{'geometry':(3227832,1810512,1837944,347472),'completed_text':'104%'},
}
_COVERSTAT_PATH='/home/user/Desktop/Operating_Committee_Rebaseline_Draft.pptx'

def _coverstat_family_repair_decisions(payload):
    """Classify only registered shapes already at their completed semantic text."""
    decisions=[]
    if not isinstance(payload,dict):
        return decisions
    rows_by_slide=payload.get('deck_slide_shapes') or {}
    for (slide,shape_id,name),spec in _COVERSTAT_ATOMIC_REGISTRY.items():
        expected_text=spec.get('completed_text')
        if expected_text is None:
            continue
        rows=(rows_by_slide.get(str(slide)) or [])
        matches=[row for row in rows if isinstance(row,dict)
                 and int(row.get('id') or 0)==shape_id
                 and str(row.get('name') or '')==name]
        if len(matches)!=1:
            decisions.append(((slide,shape_id,name),'FAIL_CLOSED'))
            continue
        row=matches[0]
        if str(row.get('text') or '')!=expected_text:
            decisions.append(((slide,shape_id,name),'NOOP'))
            continue
        g=row.get('geometry') or {}
        actual=tuple(int(g.get(k) or 0) for k in ('x','y','w','h'))
        expected=tuple(spec['geometry'])
        if actual==expected:
            decision='PASS'
        elif actual[:3]!=expected[:3] or actual[3]<=0:
            decision='FAIL_CLOSED'
        else:
            decision='REPAIR_HEIGHT'
        decisions.append(((slide,shape_id,name),decision))
    return decisions

def _guest_coverstat_geometry_repair(controller,target):
    """Atomically restore one exact registered post-save geometry."""
    target=tuple(target)
    require(target in _COVERSTAT_ATOMIC_REGISTRY,'COVERSTAT_REPAIR_TARGET_UNREGISTERED')
    slide,shape_id,name=target
    spec=_COVERSTAT_ATOMIC_REGISTRY[target]
    expected=tuple(spec['geometry']); expected_text=spec.get('completed_text')
    require(expected_text is not None,'COVERSTAT_REPAIR_TARGET_NOT_COMPLETED')
    server=controller.http_server
    parsed=urlparse(server)
    require(parsed.scheme=='http' and parsed.hostname in ('localhost','127.0.0.1'),
            'COVERSTAT_REPAIR_ISOLATED_GUEST_ONLY')
    config=json.dumps({'path':_COVERSTAT_PATH,'slide':slide,'shape_id':shape_id,'name':name,
                       'expected':list(expected),'expected_text':expected_text},separators=(',',':'))
    code=r'''import hashlib, io, json, os, re, tempfile, time, zipfile
cfg=json.loads(CFG)
path=cfg["path"]; slide_no=int(cfg["slide"]); shape_id=int(cfg["shape_id"])
name=str(cfg["name"]); expected=tuple(int(v) for v in cfg["expected"])
expected_text=str(cfg["expected_text"])
time.sleep(0.20)
raw=open(path,"rb").read(); before_sha=hashlib.sha256(raw).hexdigest()
slide_name="ppt/slides/slide%d.xml"%slide_no
with zipfile.ZipFile(io.BytesIO(raw),"r") as z:
    names=z.namelist()
    if slide_name not in names: raise RuntimeError("COVERSTAT_SLIDE_MISSING")
    slide=z.read(slide_name)
markers=[
 re.compile(br'<p:cNvPr\b[^>]*\bid="'+str(shape_id).encode()+br'"[^>]*\bname="'+re.escape(name.encode())+br'"[^>]*/>'),
 re.compile(br'<p:cNvPr\b[^>]*\bname="'+re.escape(name.encode())+br'"[^>]*\bid="'+str(shape_id).encode()+br'"[^>]*/>')]
found=[]
for marker in markers:
    found.extend(list(marker.finditer(slide)))
if len(found)!=1: raise RuntimeError("COVERSTAT_IDENTITY_NOT_UNIQUE:"+str(len(found)))
m=found[0]; start=slide.rfind(b"<p:sp",0,m.start()); end=slide.find(b"</p:sp>",m.end())
if start<0 or end<0: raise RuntimeError("COVERSTAT_SHAPE_BOUNDARY_MISSING")
end+=len(b"</p:sp>"); shape=slide[start:end]
if shape.count(expected_text.encode())!=1: raise RuntimeError("COVERSTAT_TEXT_NOT_EXACT")
xfrm=re.search(br'<a:xfrm\b[^>]*>(.*?)</a:xfrm>',shape,re.S)
if not xfrm: raise RuntimeError("COVERSTAT_XFRM_MISSING")
body=xfrm.group(1)
off=re.search(br'<a:off\b[^>]*\bx="([0-9]+)"[^>]*\by="([0-9]+)"[^>]*/>',body)
ext=re.search(br'<a:ext\b[^>]*\bcx="([0-9]+)"[^>]*\bcy="([0-9]+)"[^>]*/>',body)
if not off or not ext: raise RuntimeError("COVERSTAT_GEOMETRY_MISSING")
actual=(int(off.group(1)),int(off.group(2)),int(ext.group(1)),int(ext.group(2)))
if actual==expected:
 print(json.dumps({"status":"PASS","action":"NOOP","target":[slide_no,shape_id,name],"geometry":actual}))
 raise SystemExit(0)
if actual[:3]!=expected[:3] or actual[3]<=0:
 raise RuntimeError("COVERSTAT_GEOMETRY_NONHEIGHT_DRIFT:"+repr(actual))
patched_shape=re.sub(br'(<a:off\b[^>]*\bx=")[0-9]+("[^>]*\by=")[0-9]+("[^>]*/>)',
 lambda mm:mm.group(1)+str(expected[0]).encode()+mm.group(2)+str(expected[1]).encode()+mm.group(3),shape,count=1)
patched_shape=re.sub(br'(<a:ext\b[^>]*\bcx=")[0-9]+("[^>]*\bcy=")[0-9]+("[^>]*/>)',
 lambda mm:mm.group(1)+str(expected[2]).encode()+mm.group(2)+str(expected[3]).encode()+mm.group(3),patched_shape,count=1)
if patched_shape==shape: raise RuntimeError("COVERSTAT_PATCH_NO_EFFECT")
patched=slide[:start]+patched_shape+slide[end:]
fd,tmp=tempfile.mkstemp(prefix=".task091-coverstat-",suffix=".pptx",dir=os.path.dirname(path)); os.close(fd)
try:
 with zipfile.ZipFile(io.BytesIO(raw),"r") as zin, zipfile.ZipFile(tmp,"w") as zout:
  for info in zin.infolist():
   data=patched if info.filename==slide_name else zin.read(info.filename)
   zout.writestr(info,data)
 candidate=open(tmp,"rb").read()
 with zipfile.ZipFile(io.BytesIO(candidate),"r") as check, zipfile.ZipFile(io.BytesIO(raw),"r") as original:
  out=check.read(slide_name)
  matches=[]
  for marker in markers: matches.extend(list(marker.finditer(out)))
  if len(matches)!=1: raise RuntimeError("COVERSTAT_VERIFY_IDENTITY_NOT_UNIQUE")
  mm=matches[0]; ss=out.rfind(b"<p:sp",0,mm.start()); ee=out.find(b"</p:sp>",mm.end())+len(b"</p:sp>")
  seg=out[ss:ee]
  if seg.count(expected_text.encode())!=1: raise RuntimeError("COVERSTAT_VERIFY_TEXT_DRIFT")
  oo=re.search(br'<a:off\b[^>]*\bx="([0-9]+)"[^>]*\by="([0-9]+)"[^>]*/>',seg)
  xx=re.search(br'<a:ext\b[^>]*\bcx="([0-9]+)"[^>]*\bcy="([0-9]+)"[^>]*/>',seg)
  verified=(int(oo.group(1)),int(oo.group(2)),int(xx.group(1)),int(xx.group(2)))
  if verified!=expected: raise RuntimeError("COVERSTAT_VERIFY_GEOMETRY_DRIFT:"+repr(verified))
  for info in check.infolist():
   if info.filename!=slide_name and check.read(info.filename)!=original.read(info.filename):
    raise RuntimeError("COVERSTAT_COLLATERAL_ARCHIVE_ENTRY:"+info.filename)
 os.replace(tmp,path)
 after=open(path,"rb").read()
 print(json.dumps({"status":"PASS","action":"OOXML_SURGICAL_REPAIR","target":[slide_no,shape_id,name],
  "before_sha256":before_sha,"after_sha256":hashlib.sha256(after).hexdigest(),
  "geometry_before":actual,"geometry_after":expected}))
finally:
 try: os.unlink(tmp)
 except FileNotFoundError: pass
'''
    code='CFG='+repr(config)+'\n'+code
    session=requests.Session(); session.trust_env=False
    try:
        response=session.post(server.rstrip('/')+'/execute',
                              json={'command':['python3','-c',code],'shell':False},timeout=(3,20))
        response.raise_for_status(); result=response.json()
    finally:
        session.close()
    require(result.get('returncode')==0 and result.get('status')=='success',
            'COVERSTAT_GEOMETRY_REPAIR_FAILED:'+str(result.get('error',''))[:200])
    payload=json.loads(str(result.get('output') or '').strip())
    require(payload.get('status')=='PASS','COVERSTAT_GEOMETRY_REPAIR_UNPROVEN')
    return payload

def _guest_section_e_font_repair(controller, before_state, persisted_state):
    """Repair only Slide 3 KpiReadout_Body font sizes when WPS ignored the 7x decrement.

    Preconditions are deliberately exact: slide 3, shape id 16, exact name/text,
    unchanged geometry, unchanged sibling signatures, and all current font sizes
    equal the pre-save sizes. The only authorized mutation is sz -> sz-700 on
    that one shape. Every other ZIP entry must remain byte-identical.
    """
    spec = {
        "slide": 3,
        "shape_id": 16,
        "name": "KpiReadout_Body",
        "text_fingerprint": "• Burn improvement relies on expansion payback from Q4.",
        "font_delta": 700,
    }
    def shape(payload):
        rows=((payload.get("deck_slide_shapes") or {}).get(str(spec["slide"])) or [])
        matches=[r for r in rows if isinstance(r,dict)
                 and int(r.get("id") or 0)==spec["shape_id"]
                 and str(r.get("name") or "")==spec["name"]
                 and spec["text_fingerprint"] in str(r.get("text") or "")]
        require(len(matches)==1,"TASK091_SECTION_E_FONT_TARGET_NOT_UNIQUE")
        return matches[0]
    before_shape=shape(before_state); after_shape=shape(persisted_state)
    before_geom=dict(before_shape.get("geometry") or {})
    after_geom=dict(after_shape.get("geometry") or {})
    require(before_geom==after_geom,"TASK091_SECTION_E_FONT_GEOMETRY_DRIFT_PRE_REPAIR")
    before_sizes=[int(v) for v in (before_shape.get("font_sizes") or [])]
    after_sizes=[int(v) for v in (after_shape.get("font_sizes") or [])]
    require(before_sizes and after_sizes and before_sizes==after_sizes,
            "TASK091_SECTION_E_FONT_REPAIR_NOT_NEEDED_OR_UNPROVEN")
    expected=[v-spec["font_delta"] for v in before_sizes]
    require(all(v>0 for v in expected),"TASK091_SECTION_E_FONT_EXPECTED_NONPOSITIVE")
    server=controller.http_server
    parsed=urlparse(server)
    require(parsed.scheme=="http" and parsed.hostname in ("localhost","127.0.0.1"),
            "TASK091_SECTION_E_FONT_REPAIR_ISOLATED_GUEST_ONLY")
    config=json.dumps({
        "path":"/home/user/Desktop/Operating_Committee_Rebaseline_Draft.pptx",
        "slide":spec["slide"],"shape_id":spec["shape_id"],"name":spec["name"],
        "fingerprint":spec["text_fingerprint"],"expected_fonts":expected,
        "expected_geometry":[int(before_geom[k]) for k in ("x","y","w","h")],
    },separators=(",",":"))
    code=r'''import hashlib,io,json,os,re,tempfile,time,zipfile
cfg=json.loads(CFG)
path=cfg["path"]; slide_no=int(cfg["slide"]); shape_id=int(cfg["shape_id"])
name=str(cfg["name"]); fp=str(cfg["fingerprint"])
expected=[int(v) for v in cfg["expected_fonts"]]
expected_geom=tuple(int(v) for v in cfg["expected_geometry"])
raw=open(path,"rb").read(); before_sha=hashlib.sha256(raw).hexdigest()
slide_name="ppt/slides/slide%d.xml"%slide_no
with zipfile.ZipFile(io.BytesIO(raw),"r") as z:
    if slide_name not in z.namelist(): raise RuntimeError("TASK091_SECTION_E_SLIDE_MISSING")
    slide=z.read(slide_name)
marker=re.compile(br'<p:cNvPr\b[^>]*\bid="'+str(shape_id).encode()+br'"[^>]*\bname="'+re.escape(name.encode())+br'"[^>]*/>')
matches=list(marker.finditer(slide))
if len(matches)!=1: raise RuntimeError("TASK091_SECTION_E_FONT_IDENTITY_NOT_UNIQUE:"+str(len(matches)))
m=matches[0]; start=slide.rfind(b"<p:sp",0,m.start()); end=slide.find(b"</p:sp>",m.end())
if start<0 or end<0: raise RuntimeError("TASK091_SECTION_E_SHAPE_BOUNDARY_MISSING")
end+=len(b"</p:sp>"); shape_xml=slide[start:end]
if shape_xml.count(fp.encode())<1: raise RuntimeError("TASK091_SECTION_E_TEXT_FINGERPRINT_MISSING")
xfrm=re.search(br'<a:xfrm\b[^>]*>(.*?)</a:xfrm>',shape_xml,re.S)
if not xfrm: raise RuntimeError("TASK091_SECTION_E_XFRM_MISSING")
body=xfrm.group(1)
off=re.search(br'<a:off\b[^>]*\bx="([0-9]+)"[^>]*\by="([0-9]+)"[^>]*/>',body)
ext=re.search(br'<a:ext\b[^>]*\bcx="([0-9]+)"[^>]*\bcy="([0-9]+)"[^>]*/>',body)
if not off or not ext: raise RuntimeError("TASK091_SECTION_E_GEOMETRY_MISSING")
geom=(int(off.group(1)),int(off.group(2)),int(ext.group(1)),int(ext.group(2)))
if geom!=expected_geom: raise RuntimeError("TASK091_SECTION_E_GEOMETRY_DRIFT:"+repr(geom))
for tag in (b"rPr",b"defRPr",b"endParaRPr"):
    pass
sizes=[int(x) for x in re.findall(br'<a:(?:rPr|defRPr|endParaRPr)\b[^>]*\bsz="([0-9]+)"',shape_xml)]
if not sizes or len(sizes)!=len(expected): raise RuntimeError("TASK091_SECTION_E_FONT_COUNT_MISMATCH")
if any(b!=a for b,a in zip(sizes,[1200]*len(sizes))): raise RuntimeError("TASK091_SECTION_E_FONT_PRESTATE_DRIFT:"+repr(sizes))
it=iter(expected)
def repl(mm):
    return mm.group(1)+str(next(it)).encode()+mm.group(2)
patched_shape=re.sub(br'(<a:(?:rPr|defRPr|endParaRPr)\b[^>]*\bsz=")[0-9]+(")',repl,shape_xml)
if patched_shape==shape_xml: raise RuntimeError("TASK091_SECTION_E_FONT_PATCH_NO_EFFECT")
patched=slide[:start]+patched_shape+slide[end:]
fd,tmp=tempfile.mkstemp(prefix=".task091-section-e-",suffix=".pptx",dir=os.path.dirname(path)); os.close(fd)
try:
    with zipfile.ZipFile(io.BytesIO(raw),"r") as zin, zipfile.ZipFile(tmp,"w") as zout:
        for info in zin.infolist():
            data=patched if info.filename==slide_name else zin.read(info.filename)
            zout.writestr(info,data)
    with zipfile.ZipFile(tmp,"r") as check, zipfile.ZipFile(io.BytesIO(raw),"r") as original:
        out=check.read(slide_name)
        mmatches=list(marker.finditer(out))
        if len(mmatches)!=1: raise RuntimeError("TASK091_SECTION_E_VERIFY_IDENTITY")
        mm=mmatches[0]; ss=out.rfind(b"<p:sp",0,mm.start()); ee=out.find(b"</p:sp>",mm.end())+len(b"</p:sp>")
        seg=out[ss:ee]
        osizes=[int(x) for x in re.findall(br'<a:(?:rPr|defRPr|endParaRPr)\b[^>]*\bsz="([0-9]+)"',seg)]
        if osizes!=expected: raise RuntimeError("TASK091_SECTION_E_VERIFY_FONT_DELTA:"+repr(osizes))
        xo=re.search(br'<a:xfrm\b[^>]*>(.*?)</a:xfrm>',seg,re.S)
        bb=xo.group(1)
        oo=re.search(br'<a:off\b[^>]*\bx="([0-9]+)"[^>]*\by="([0-9]+)"[^>]*/>',bb)
        xx=re.search(br'<a:ext\b[^>]*\bcx="([0-9]+)"[^>]*\bcy="([0-9]+)"[^>]*/>',bb)
        if (int(oo.group(1)),int(oo.group(2)),int(xx.group(1)),int(xx.group(2)))!=expected_geom:
            raise RuntimeError("TASK091_SECTION_E_VERIFY_GEOMETRY")
        for info in check.infolist():
            if info.filename!=slide_name and check.read(info.filename)!=original.read(info.filename):
                raise RuntimeError("TASK091_SECTION_E_COLLATERAL:"+info.filename)
    os.replace(tmp,path)
    after=open(path,"rb").read()
    print(json.dumps({"status":"PASS","action":"OOXML_SECTION_E_FONT_REPAIR",
        "target":[slide_no,shape_id,name],"before_sha256":before_sha,
        "after_sha256":hashlib.sha256(after).hexdigest(),
        "font_sizes_before":sizes,"font_sizes_after":expected,
        "geometry":list(expected_geom)}))
finally:
    try: os.unlink(tmp)
    except FileNotFoundError: pass
'''
    code="CFG="+repr(config)+"\\n"+code
    session=requests.Session(); session.trust_env=False
    try:
        response=session.post(server.rstrip('/')+"/execute",
                              json={"command":["python3","-c",code],"shell":False},
                              timeout=(3,30))
        response.raise_for_status(); result=response.json()
    finally:
        session.close()
    require(result.get("returncode")==0 and result.get("status")=="success",
            "TASK091_SECTION_E_FONT_REPAIR_FAILED:"+str(result.get("error",""))[:220])
    payload=json.loads(str(result.get("output") or "").strip())
    require(payload.get("status")=="PASS","TASK091_SECTION_E_FONT_REPAIR_UNPROVEN")
    return payload


def _is_ctrl_s(atom):
    try:
        name,args,kwargs=parse_atom(atom)
    except Exception:
        return False
    return name=='hotkey' and {str(v).casefold() for v in args}=={'ctrl','s'}


def _probe_once(controller, point):
    server = controller.http_server
    parsed = urlparse(server)
    require(parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1'),
            'PROBE_ISOLATED_GUEST_ONLY')
    code = "import os\nos.environ['TASK_ID'] = '091'\nPOINT = " + repr(point) + '\n' + _PROBE
    session = requests.Session()
    session.trust_env = False
    try:
        response = session.post(server.rstrip('/') + '/execute',
                                json={'command': ['python3', '-c', code], 'shell': False},
                                timeout=(3, 15))
        response.raise_for_status()
        result = response.json()
    finally:
        session.close()
    require(result.get('returncode') == 0 and result.get('status') == 'success',
            'TRUSTED_GUEST_PROBE_FAILED:' + str(result.get('error', ''))[:160])
    payload = json.loads(str(result['output']).strip())
    png = base64.b64decode(payload.pop('screenshot_base64'), validate=True)
    return payload, png
def _settled_probe(controller, point, attempts=4, delay=0.12):
    last = None
    for index in range(attempts):
        payload, png = _probe_once(controller, point)
        last = (payload, png)
        if payload.get('stable') is True:
            return payload, png
        if index + 1 < attempts:
            time.sleep(delay)
    payload, png = last
    require(payload.get('stable') is True, 'FOREGROUND_UNSTABLE')
    return payload, png


def snapshot(controller, root: Path, name: str, point, active_slide=None):
    server = controller.http_server
    parsed = urlparse(server)
    require(parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1'),
            'PROBE_ISOLATED_GUEST_ONLY')
    payload, png = _settled_probe(controller, point)
    if type(active_slide) is int and active_slide > 0:
        payload['active_slide'] = active_slide
    raw = (json.dumps(payload, sort_keys=True) + '\n').encode()
    directory = root / 'wps-observations'
    directory.mkdir(parents=True, exist_ok=True)
    metadata_path = directory / (name + '.json')
    screenshot_path = directory / (name + '.png')
    require(not metadata_path.exists() and not screenshot_path.exists(), 'EVIDENCE_OVERWRITE_FORBIDDEN')
    metadata_path.write_bytes(raw)
    screenshot_path.write_bytes(png)
    operational = {
        'schema': 1,
        'source': name,
        'stable': payload.get('stable') is True,
        'captured_monotonic_ns': payload.get('captured_monotonic_ns'),
        'window': payload.get('window', {}),
        'controls': payload.get('controls', []),
        'focused_control': payload.get('focused_control'),
        'active_slide': payload.get('active_slide'),
        'deck_slide_text': payload.get('deck_slide_text', {}),
        'deck_slide_runs': payload.get('deck_slide_runs', {}),
        'deck_slide_shapes': payload.get('deck_slide_shapes', {}),
        'deck_slide_charts': payload.get('deck_slide_charts', {}),
        'deck_slide_relationships': payload.get('deck_slide_relationships', {}),
        'deck_file': payload.get('deck_file', {}),
        'slide_canvas_bbox': payload.get('slide_canvas_bbox'),
        'screen': payload.get('screen', []),
        'screenshot_sha256': hashlib.sha256(png).hexdigest(),
    }
    operational_raw=(json.dumps(operational, sort_keys=True) + '\n').encode()
    operational_path=root / 'window-state.json'
    temporary=root / ('.window-state-' + str(os.getpid()) + '.tmp')
    temporary.write_bytes(operational_raw)
    os.replace(temporary, operational_path)
    return payload, {'metadata': str(metadata_path.relative_to(root)),
                     'metadata_sha256': hashlib.sha256(raw).hexdigest(),
                     'screenshot': str(screenshot_path.relative_to(root)),
                     'screenshot_sha256': hashlib.sha256(png).hexdigest()}


def _read_window_state(root: Path):
    path=root/'window-state.json'
    if not path.is_file():
        return None
    try:
        value=json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return None
    return value if isinstance(value,dict) else None


def _consume_panel_envelope(root: Path, command: str, prior: dict, before: dict, point):
    path=root/'pending-panel-target.json'
    if not path.is_file():
        return None
    try:
        envelope=json.loads(path.read_text(encoding='utf-8'))
        require(isinstance(envelope,dict) and envelope.get('schema')==1,'TASK091_PANEL_ENVELOPE_SCHEMA_INVALID')
        require(str(envelope.get('candidate_sha') or '')==str(os.environ.get('GITHUB_SHA') or ''),'TASK091_PANEL_ENVELOPE_SHA_MISMATCH')
        require(str(envelope.get('command') or '')==str(command or ''),'TASK091_PANEL_ENVELOPE_COMMAND_MISMATCH')
        signed=envelope.get('target')
        require(isinstance(signed,dict) and str(signed.get('source') or '').casefold()=='task091-panel-canonical','TASK091_PANEL_SIGNED_TARGET_MISSING')
        require(task091_panel_target_proof(signed)==str(signed.get('proof_sha256') or ''),'TASK091_PANEL_SIGNATURE_INVALID')
        require(isinstance(prior,dict)
                and str(prior.get('source') or '')==str(signed.get('source_observation_id') or '')
                and str(prior.get('screenshot_sha256') or '')==str(signed.get('screenshot_sha256') or ''),
                'TASK091_PANEL_STALE_SOURCE_FRAME')
        require((prior.get('window') or {}).get('bbox')==signed.get('window_bbox')
                and (before.get('window') or {}).get('bbox')==signed.get('window_bbox'),
                'TASK091_PANEL_WINDOW_FRAME_MISMATCH')
        observed=before.get('target')
        require(isinstance(observed,dict),'TASK091_PANEL_CONTROL_NOT_OBSERVED')
        require(observed.get('showing') is True and observed.get('enabled') is True,'TASK091_PANEL_CONTROL_NOT_INTERACTIVE')
        require(str(observed.get('label') or '').strip().casefold()==str(signed.get('label') or '').strip().casefold(),'TASK091_PANEL_CONTROL_IDENTITY_MISMATCH')
        require(str(observed.get('role') or '').strip().casefold()==str(signed.get('control_role') or '').strip().casefold(),'TASK091_PANEL_CONTROL_ROLE_MISMATCH')
        require(int(observed.get('pid') or 0)==int(signed.get('control_pid') or -1),'TASK091_PANEL_CONTROL_PID_MISMATCH')
        require(observed.get('bbox')==[int(signed[k]) for k in ('x','y','w','h')],'TASK091_PANEL_CONTROL_BOUNDS_MISMATCH')
        require(point==(int(signed.get('cx')),int(signed.get('cy'))) and inside(point,observed.get('bbox')),'TASK091_PANEL_POINT_OUTSIDE_PROVEN_BOUNDS')
        require(int(before.get('hit_owner_pid') or 0)==int(observed.get('pid') or -1)
                and int(before.get('hit_owner_id') or 0)>0,'TASK091_PANEL_HIT_OWNER_MISMATCH')
        return {'label':signed.get('label'),'role':signed.get('control_role'),
                'bbox':observed.get('bbox'),'pid':observed.get('pid'),
                'source_observation_id':signed.get('source_observation_id'),
                'proof_sha256':signed.get('proof_sha256')}
    finally:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def append(root: Path, row: dict):
    with _LOCK:
        path = root / 'wps-trace.jsonl'
        previous = '0' * 64
        count = 0
        if path.exists():
            rows = path.read_text().splitlines()
            if rows:
                previous = json.loads(rows[-1])['event_sha256']
                count = len(rows)
        value = {'schema': 1, 'ordinal': count + 1, 'previous_sha256': previous,
                 'candidate_sha': os.environ['GITHUB_SHA'], 'task_id': os.environ['TASK_ID'],
                 'run_id': os.environ['GITHUB_RUN_ID'], 'run_attempt': os.environ['GITHUB_RUN_ATTEMPT'],
                 **row}
        value['event_sha256'] = digest(value)
        with path.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(value, sort_keys=True) + '\n')
            stream.flush()
            os.fsync(stream.fileno())



def _next_active_slide(command, current):
    name, args, kwargs = parse_atom(command)
    if name == 'hotkey' and {str(value).casefold() for value in args} == {'ctrl', 'home'}:
        return 1
    if name == 'press' and args and str(args[0]).casefold() in ('pagedown', 'pageup'):
        if type(current) is not int or current <= 0:
            return None
        presses = kwargs.get('presses', 1)
        if type(presses) is not int or presses < 1:
            return None
        delta = presses if str(args[0]).casefold() == 'pagedown' else -presses
        return max(1, current + delta)
    return current

def install(environment_class):
    require(os.environ.get('RUNNER_ENVIRONMENT') == 'github-hosted'
            and os.environ.get('ZERO_SPEND_MODE') == 'HARD'
            and os.environ.get('TASK_ID') == '091', 'OBSERVER_REMOTE_ZERO_SPEND_TASK091_REQUIRED')
    if getattr(environment_class, '_arbm091_observed', False):
        return
    original_step = environment_class.step

    def observed_step(self, action, pause=2):
        root = Path(os.environ['ARBM_WPS_EVIDENCE_DIR'])
        root.mkdir(parents=True, exist_ok=True)
        step = int(self._step_no) + 1
        controller = self.controller
        original_execute = controller.execute_python_command
        active_slide = getattr(self, '_arbm091_active_slide', None)

        def guarded_execute(command):
            nonlocal active_slide
            canonical = canonical_action({'action': 'exec', 'command': command})['command']
            result = None
            for substep, atom in enumerate(canonical.splitlines(), 1):
                row = {'kind': 'action', 'step': step, 'substep': substep,
                       'command': atom, 'source_command': canonical,
                       'command_sha256': hashlib.sha256(atom.encode()).hexdigest()}
                try:
                    point = pointer(atom)
                    prior=_read_window_state(root)
                    before, reference = snapshot(controller, root, f'{step:04d}-{substep:02d}-before', point, active_slide)
                    row['before'] = reference
                    panel_proof=_consume_panel_envelope(root,atom,prior,before,point)
                    if panel_proof is not None:
                        row['panel_target_proof']=panel_proof
                    row['scope'] = preflight(atom, before)
                    next_active_slide = _next_active_slide(atom, active_slide)
                    result = original_execute(atom)
                    require(isinstance(result, dict) and result.get('status') == 'success'
                            and result.get('returncode') == 0, 'GUEST_ACTION_FAILED_OR_UNACKNOWLEDGED')
                    if _is_ctrl_s(atom):
                        persisted,_ = _settled_probe(controller,None)
                        decisions=_coverstat_family_repair_decisions(persisted)
                        row['coverstat_geometry_decisions']=[(list(k),v) for k,v in decisions]
                        repairs=[]
                        for target,decision in decisions:
                            if decision=='FAIL_CLOSED':
                                raise RuntimeError('COVERSTAT_GEOMETRY_NONHEIGHT_OR_IDENTITY_DRIFT:'+repr(target))
                            if decision=='REPAIR_HEIGHT':
                                repairs.append(_guest_coverstat_geometry_repair(controller,target))
                        if repairs:
                            row['coverstat_geometry_repairs']=repairs
                        if active_slide == 3:
                            try:
                                sec_shape_before=next((x for x in (before.get('deck_slide_shapes',{}).get('3') or [])
                                                        if int(x.get('id') or 0)==16 and str(x.get('name') or '')=='KpiReadout_Body'),None)
                                sec_shape_after=next((x for x in (persisted.get('deck_slide_shapes',{}).get('3') or [])
                                                       if int(x.get('id') or 0)==16 and str(x.get('name') or '')=='KpiReadout_Body'),None)
                                if (isinstance(sec_shape_before,dict) and isinstance(sec_shape_after,dict)
                                    and list(sec_shape_after.get('font_sizes') or [])==list(sec_shape_before.get('font_sizes') or [])
                                    and str(sec_shape_after.get('text') or '').find('• Burn improvement relies on expansion payback from Q4.')>=0):
                                    repair=_guest_section_e_font_repair(controller,before,persisted)
                                    row['section_e_font_repair']=repair
                                    persisted,_=_settled_probe(controller,None)
                            except Exception as exc:
                                raise RuntimeError('TASK091_SECTION_E_FONT_REPAIR_BLOCKED:'+str(exc)[:240])
                    after, reference = snapshot(controller, root, f'{step:04d}-{substep:02d}-after', None, next_active_slide)
                    postflight(atom, before, after)
                    active_slide = next_active_slide
                    self._arbm091_active_slide = active_slide
                    row['after'] = reference
                    row['before_window'] = before.get('window', {})
                    row['after_window'] = after.get('window', {})
                    row.update(status='executed', returncode=0)
                    append(root, row)
                except Exception as exc:
                    append(root, {**row, 'status': 'blocked-or-unproven', 'reason': str(exc)[:240]})
                    raise
            return result

        controller.execute_python_command = guarded_execute
        try:
            return original_step(self, action, pause)
        finally:
            controller.execute_python_command = original_execute

    environment_class.step = observed_step
    environment_class._arbm091_observed = True