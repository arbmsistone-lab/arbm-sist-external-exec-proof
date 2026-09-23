"""Deterministic structural contract for OSWorld Task 091.

Values are transcribed from the pinned official Task 091 evaluator and its
pinned Reforecast_Model_H2.xlsx source.  This module never mutates the deck.
"""
from __future__ import annotations

import math

TASK091_OFFICIAL_CONTRACT_SHA256="fa858d17ac5a40794d46f53354470e17da2b1865215f34fc14591e05df2462db"
TASK091_SOURCE_WORKBOOK_SHA256="9009b83f13787cd556241dad228cbcda00163efa587a1466a9b0e0a746e2c61a"
TASK091_BASELINE_DECK_SHA256="4c9c57567fa8f4bd81175dbd3d1b2ea40f0ad1ff8689ca47e1cbd001da637f5b"

EMU_PER_INCH=914400
RISK_GRID_LEFT=int(1.35*EMU_PER_INCH)
RISK_GRID_TOP=int(1.85*EMU_PER_INCH)
RISK_CELL_W=int(1.55*EMU_PER_INCH)
RISK_CELL_H=int(1.28*EMU_PER_INCH)
EXPECTED_CUSTOMER_RETENTION_RGB="92D050"

EXPECTED_RESOURCE_TOTALS={
    "platform":6.2,
    "reliability":3.9,
    "product":5.8,
    "gtm":6.5,
    "growth ops":2.0,
    "g&a":4.0,
}
EXPECTED_HC_FINAL={
    "platform":45.0,
    "reliability":18.0,
    "product":47.0,
    "gtm":65.0,
    "growth ops":16.0,
    "g&a":15.0,
}
EXPECTED_OPEN_ROLES={
    "platform":2.0,
    "reliability":3.0,
    "product":1.0,
    "gtm":2.0,
    "growth ops":0.0,
    "g&a":0.0,
}
EXPECTED_RISK_CELLS={
    "cloud migration slip":(3,3),
    "support queue backlog":(3,3),
    "pricing rollout adoption":(1,2),
    "analytics latency":(2,2),
    "vendor sla breach":(2,3),
    "data migration cutover failure":(3,2),
}
EXPECTED_ROADMAP_LANES=(
    "core platform",
    "reliability hardening",
    "data migration",
    "revenue ops automation",
    "customer retention plays",
)
EXPECTED_ROADMAP_SPANS={
    "core platform":(0,3),
    "reliability hardening":(0,5),
    "data migration":(1,5),
    "revenue ops automation":(0,5),
    "customer retention plays":(2,4),
}
BRIDGE_TERMS=(
    "base arr","renewal saves","pricing discipline","migration delay",
    "support credits","international pilot stop","partner stabilization","h2 exit arr",
)
BRIDGE_VALUES=("39.6","0.7","0.4","-0.6","-0.5","-0.3","1.6","40.9")
GLOBAL_STALE_TERMS=(
    "expansion sprint","accelerating","ahead of plan","scale-up mode",
    "growth-focused","commercial scale-up","platform & reliability",
)


class StructuralContractError(ValueError):
    pass


def _norm(value):
    return " ".join(str(value or "").casefold().replace("\u200b","").split())


def _approx(a,b,tol=0.15):
    return abs(float(a)-float(b))<=float(tol)


def _shapes(state,slide):
    table=state.get("deck_slide_shapes",{}) if isinstance(state,dict) else {}
    rows=table.get(str(int(slide)),[]) if isinstance(table,dict) else []
    return [r for r in rows if isinstance(r,dict)]


def _charts(state,slide):
    table=state.get("deck_slide_charts",{}) if isinstance(state,dict) else {}
    rows=table.get(str(int(slide)),[]) if isinstance(table,dict) else []
    return [r for r in rows if isinstance(r,dict)]


def _slide_text(state,slide):
    return _norm(" ".join(str(r.get("text") or "") for r in _shapes(state,slide)))


def _all_text(state):
    table=state.get("deck_slide_shapes",{}) if isinstance(state,dict) else {}
    return _norm(" ".join(str(r.get("text") or "")
                          for rows in table.values() if isinstance(rows,list)
                          for r in rows if isinstance(r,dict)))


def _chart_one(state,slide):
    rows=_charts(state,slide)
    if len(rows)!=1:
        raise StructuralContractError(f"TASK091_SLIDE_{slide}_CHART_COUNT_INVALID:{len(rows)}")
    return rows[0]


def _chart_totals(chart):
    cats=[_norm(v) for v in chart.get("categories") or []]
    series=chart.get("series") or []
    totals={}
    for i,cat in enumerate(cats):
        total=0.0
        for row in series:
            vals=row.get("values") or []
            if i<len(vals):
                total+=float(vals[i] or 0.0)
        totals[cat]=round(total,1)
    return totals


def _risk_cell(rect):
    if not isinstance(rect,(list,tuple)) or len(rect)!=4:
        return None
    left,top,width,height=(int(v) for v in rect)
    right=left+width; bottom=top+height
    best=None; best_area=0
    for r in range(3):
        for c in range(3):
            l=RISK_GRID_LEFT+c*RISK_CELL_W
            t=RISK_GRID_TOP+r*RISK_CELL_H
            rr=l+RISK_CELL_W; bb=t+RISK_CELL_H
            area=max(0,min(right,rr)-max(left,l))*max(0,min(bottom,bb)-max(top,t))
            if area>best_area:
                best_area=area; best=(r+1,c+1)
    return best if best_area>0 else None


def _rect_overlap(a,b):
    al,at,aw,ah=(int(v) for v in a); bl,bt,bw,bh=(int(v) for v in b)
    return max(0,min(al+aw,bl+bw)-max(al,bl))*max(0,min(at+ah,bt+bh)-max(at,bt))


def _risk_associated_block(state,text_row,cell):
    geom=tuple((text_row.get("geometry") or {}).get(k,0) for k in ("x","y","w","h"))
    if len(geom)!=4 or min(geom[2:])<=0:
        return False
    pad=int(0.22*EMU_PER_INCH)
    padded=(geom[0]-pad,geom[1]-pad,geom[2]+2*pad,geom[3]+2*pad)
    for row in _shapes(state,7):
        if not row.get("fill_rgb"):
            continue
        rgeom=tuple((row.get("geometry") or {}).get(k,0) for k in ("x","y","w","h"))
        if len(rgeom)!=4 or min(rgeom[2:])<=0:
            continue
        if _risk_cell(rgeom)!=cell:
            continue
        if row is text_row:
            return True
        if _rect_overlap(padded,rgeom)>0:
            return True
    return False


def _find_text_rows(state,slide,needle):
    wanted=_norm(needle)
    return [r for r in _shapes(state,slide) if wanted and wanted in _norm(r.get("text"))]


def _month_centers(state):
    names=("jul","aug","sep","oct","nov","dec")
    centers=[]
    for name in names:
        rows=[r for r in _shapes(state,9) if _norm(r.get("text"))==name]
        if len(rows)!=1:
            return []
        g=rows[0].get("geometry") or {}
        centers.append(int(g.get("x") or 0)+int(g.get("w") or 0)//2)
    return centers if all(a<b for a,b in zip(centers,centers[1:])) else []


def _month_ranges(centers):
    if len(centers)!=6:
        return []
    gaps=[centers[i+1]-centers[i] for i in range(5)]
    if not gaps or min(gaps)<=0:
        return []
    first=centers[0]-gaps[0]//2
    last=centers[-1]+gaps[-1]//2
    bounds=[first]+[(centers[i]+centers[i+1])//2 for i in range(5)]+[last]
    return [(bounds[i],bounds[i+1]) for i in range(6)]


def _lane_bar(state,lane):
    infos=_find_text_rows(state,9,lane)
    if not infos:
        return None
    best=None; bestw=-1
    xpad=int(0.15*EMU_PER_INCH); ytol=int(0.18*EMU_PER_INCH)
    for row in _shapes(state,9):
        if not row.get("fill_rgb"):
            continue
        g=row.get("geometry") or {}
        rect=tuple(int(g.get(k) or 0) for k in ("x","y","w","h"))
        if min(rect[2:])<=0:
            continue
        cy=rect[1]+rect[3]//2
        matched=False
        for info in infos:
            ig=info.get("geometry") or {}
            ir=tuple(int(ig.get(k) or 0) for k in ("x","y","w","h"))
            if min(ir[2:])<=0:
                continue
            icy=ir[1]+ir[3]//2
            padded=(ir[0]-xpad,ir[1]-ytol,ir[2]+2*xpad,ir[3]+2*ytol)
            if abs(cy-icy)<=ytol and _rect_overlap(padded,rect)>0:
                matched=True; break
        if matched and rect[2]>bestw:
            best=row; bestw=rect[2]
    return best


def _covered_months(bar,ranges):
    g=bar.get("geometry") or {}
    left=int(g.get("x") or 0)+int(0.08*EMU_PER_INCH)
    right=int(g.get("x") or 0)+int(g.get("w") or 0)-int(0.08*EMU_PER_INCH)
    result=[]
    for i,(ml,mr) in enumerate(ranges):
        width=max(1,mr-ml)
        overlap=max(0,min(right,mr)-max(left,ml))
        if overlap/width>=0.50:
            result.append(i)
    return result


def validate_structural_contract(state):
    evidence={}

    # Slide 4: evaluator validates final bridge labels/values and stale removals.
    s4=_slide_text(state,4)
    bridge_terms=all(term in s4 for term in BRIDGE_TERMS)
    bridge_values=all(value in s4 for value in BRIDGE_VALUES)
    bridge_old=all(term not in s4 for term in ("new logo mix","usage expansion","partner channel","price uplift"))
    evidence["bridge"]={"pass":bridge_terms and bridge_values and bridge_old}

    # Slide 5: exact category set and category totals.
    c5=_chart_one(state,5)
    totals=_chart_totals(c5)
    alloc_cats=set(totals)==set(EXPECTED_RESOURCE_TOTALS)
    alloc_vals=all(k in totals and _approx(totals[k],v) for k,v in EXPECTED_RESOURCE_TOTALS.items())
    s5=_slide_text(state,5)
    alloc_text=("reliability" in s5 and "standalone" in s5 and "platform & reliability" not in s5)
    evidence["allocation"]={"pass":alloc_cats and alloc_vals and alloc_text,
                            "totals":totals}

    # Slide 6: exact category order and exactly two named series with final HC/open roles.
    c6=_chart_one(state,6)
    cats=[_norm(v) for v in c6.get("categories") or []]
    expected_cats=list(EXPECTED_HC_FINAL)
    series=[r for r in (c6.get("series") or []) if isinstance(r,dict)]
    values=[[float(v or 0.0) for v in (r.get("values") or [])] for r in series]
    expected_hc=list(EXPECTED_HC_FINAL.values()); expected_open=list(EXPECTED_OPEN_ROLES.values())
    def same(a,b):
        return len(a)==len(b) and all(_approx(x,y) for x,y in zip(a,b))
    hc_vals=(len(values)==2 and ((same(values[0],expected_hc) and same(values[1],expected_open))
                                or (same(values[1],expected_hc) and same(values[0],expected_open))))
    names=(len(series)==2 and all(str(r.get("name") or "").strip() for r in series))
    evidence["headcount"]={"pass":cats==expected_cats and hc_vals and names,
                           "categories":cats,"series":series}

    # Slide 7: exact visible final risk set in canonical cells with associated filled block.
    risk_details={}
    risk_ok=True
    for risk,cell in EXPECTED_RISK_CELLS.items():
        rows=_find_text_rows(state,7,risk)
        good=any(_risk_cell(tuple((row.get("geometry") or {}).get(k,0) for k in ("x","y","w","h")))==cell
                 and _risk_associated_block(state,row,cell) for row in rows)
        risk_details[risk]={"pass":good,"expected_cell":cell}
        risk_ok &= good
    risk_removed="regional launch readiness" not in _slide_text(state,7)
    evidence["risk"]={"pass":bool(risk_ok and risk_removed),"items":risk_details,
                      "regional_launch_removed":risk_removed}

    # Slide 9: exact lane names, month spans and retention fill.
    centers=_month_centers(state); ranges=_month_ranges(centers)
    roadmap_items={}
    roadmap_ok=bool(ranges)
    for lane in EXPECTED_ROADMAP_LANES:
        bar=_lane_bar(state,lane)
        covered=_covered_months(bar,ranges) if bar is not None and ranges else []
        exp=EXPECTED_ROADMAP_SPANS[lane]
        span_ok=bool(covered and min(covered)==exp[0] and max(covered)==exp[1])
        rgb_ok=True
        if lane=="customer retention plays":
            rgb_ok=bool(bar is not None and str(bar.get("fill_rgb") or "").upper()==EXPECTED_CUSTOMER_RETENTION_RGB)
        good=bar is not None and span_ok and rgb_ok
        roadmap_items[lane]={"pass":good,"covered":covered,"expected":exp,
                             "fill_rgb":str((bar or {}).get("fill_rgb") or "")}
        roadmap_ok &= good
    s9=_slide_text(state,9)
    roadmap_old=("expansion sprint" not in s9 and "international pilot" not in s9)
    months=all(m in s9 for m in ("jul","aug","sep","oct","nov","dec"))
    evidence["roadmap"]={"pass":bool(roadmap_ok and roadmap_old and months),
                         "items":roadmap_items,"old_removed":roadmap_old,
                         "months_present":months}

    all_text=_all_text(state)
    stale=all(term not in all_text for term in GLOBAL_STALE_TERMS)
    # International Pilot is allowed only in the Slide 4 bridge label.
    ip_others=all("international pilot" not in _slide_text(state,slide)
                  for slide in range(1,14) if slide!=4)
    evidence["cleanup"]={"pass":bool(stale and ip_others),"critical_stale_removed":stale,
                         "international_pilot_context":ip_others}

    supporting=(
        all(x in _slide_text(state,8) for x in ("core platform","reliability hardening","data migration","revenue ops automation","customer retention play"))
        and all(x not in _slide_text(state,8) for x in ("expansion sprint","international pilot"))
        and all(x in _slide_text(state,10) for x in ("renewals dashboard v2","workflow orchestration","reliability hardening","data migration","customer retention plays"))
        and all(x not in _slide_text(state,10) for x in ("expansion sprint","international pilot"))
        and all(x in _slide_text(state,13) for x in ("incident runbook rollout","cutover rehearsal complete","recovery review with opcom"))
        and all(x not in _slide_text(state,13) for x in ("expansion sprint launch","international pilot kickoff","global launch readiness review"))
    )
    evidence["supporting"]={"pass":bool(supporting)}

    failed=[name for name,row in evidence.items() if row.get("pass") is not True]
    if failed:
        raise StructuralContractError("TASK091_STRUCTURAL_CONTRACT_FAILED:"+",".join(failed))
    return {"status":"PASS","evidence":evidence,
            "contract_sha256":TASK091_OFFICIAL_CONTRACT_SHA256,
            "workbook_sha256":TASK091_SOURCE_WORKBOOK_SHA256}
