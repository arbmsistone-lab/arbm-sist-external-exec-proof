from __future__ import annotations
from typing import Any, Mapping
from .world_model import Evidence, WorldModel, fuse_world_state

def _entity_id(slide: str, row: Mapping[str, Any]) -> str:
    kind=str(row.get("kind") or "shape")
    name=str(row.get("name") or row.get("id") or "unknown")
    return f"deck.slide{slide}.{kind}.{name}"

def evidence_from_legacy_observation(observation: Mapping[str, Any]) -> tuple[Evidence, ...]:
    deck_file=observation.get("deck_file") if isinstance(observation.get("deck_file"),dict) else {}
    version=str(deck_file.get("sha256") or deck_file.get("mtime_ns") or "unversioned")
    shape_map=observation.get("deck_slide_shapes") if isinstance(observation.get("deck_slide_shapes"),dict) else {}
    out=[]
    for slide,rows in sorted(shape_map.items(),key=lambda kv:str(kv[0])):
        if not isinstance(rows,list):
            continue
        for row in rows:
            if not isinstance(row,dict):
                continue
            entity_id=_entity_id(str(slide),row)
            geometry=row.get("geometry") if isinstance(row.get("geometry"),dict) else {}
            attrs={
                "text":str(row.get("text") or ""),
                "name":str(row.get("name") or ""),
                "kind":str(row.get("kind") or "shape"),
                "slide":int(slide) if str(slide).isdigit() else str(slide),
                "geometry":dict(geometry),
                "modality":"file",
            }
            out.append(Evidence("openxml",entity_id,version,attrs,0.98,str(deck_file.get("sha256") or "")))
    return tuple(out)

def world_from_legacy_observation(observation: Mapping[str, Any]) -> WorldModel:
    return fuse_world_state(evidence_from_legacy_observation(observation),min_confidence=0.50)