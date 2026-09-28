from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping
import hashlib
import json

@dataclass(frozen=True)
class Evidence:
    source: str
    entity_id: str
    version: str
    value: Mapping[str, Any]
    confidence: float
    sha256: str = ""

    def validate(self) -> None:
        if not self.source or not self.entity_id or not self.version:
            raise ValueError("EVIDENCE_IDENTITY_REQUIRED")
        if not (0.0 <= float(self.confidence) <= 1.0):
            raise ValueError("EVIDENCE_CONFIDENCE_RANGE")
        if self.sha256 and len(self.sha256) != 64:
            raise ValueError("EVIDENCE_SHA256_INVALID")

@dataclass(frozen=True)
class SemanticEntity:
    entity_id: str
    version: str
    attributes: Mapping[str, Any]
    sources: tuple[str, ...]
    confidence: float
    digest: str

@dataclass(frozen=True)
class WorldModel:
    entities: Mapping[str, SemanticEntity]
    revision: str
    conflicts: tuple[str, ...] = ()
    evidence_count: int = 0

    def require_entity(self, entity_id: str) -> SemanticEntity:
        if self.conflicts:
            raise RuntimeError("WORLD_MODEL_CONFLICT:"+";".join(self.conflicts))
        entity=self.entities.get(entity_id)
        if entity is None:
            raise KeyError("WORLD_ENTITY_MISSING:"+entity_id)
        return entity

def _canonical(value: Mapping[str, Any]) -> str:
    return json.dumps(value,sort_keys=True,separators=(",",":"),default=str)

def fuse_world_state(evidence: Iterable[Evidence], *, min_confidence: float=0.65) -> WorldModel:
    rows=list(evidence)
    groups: dict[str,list[Evidence]]={}
    for item in rows:
        item.validate()
        if item.confidence >= min_confidence:
            groups.setdefault(item.entity_id,[]).append(item)
    entities={}
    conflicts=[]
    for entity_id,items in groups.items():
        by_value: dict[str,list[Evidence]]={}
        for item in items:
            by_value.setdefault(_canonical(item.value),[]).append(item)
        ranked=sorted(
            by_value.items(),
            key=lambda kv:(sum(x.confidence for x in kv[1]),len(kv[1]),kv[0]),
            reverse=True,
        )
        winner_key,winner_rows=ranked[0]
        winner_score=sum(x.confidence for x in winner_rows)
        runner_score=sum(x.confidence for x in ranked[1][1]) if len(ranked)>1 else 0.0
        if runner_score and abs(winner_score-runner_score) < 0.20:
            conflicts.append(entity_id)
            continue
        attrs=json.loads(winner_key)
        sources=tuple(sorted({x.source for x in winner_rows}))
        version=max((x.version for x in winner_rows),default="")
        confidence=min(1.0,winner_score/max(1,len(winner_rows)))
        digest=hashlib.sha256((entity_id+version+winner_key+"|".join(sources)).encode()).hexdigest()
        entities[entity_id]=SemanticEntity(entity_id,version,attrs,sources,confidence,digest)
    revision=hashlib.sha256(
        json.dumps({k:v.digest for k,v in sorted(entities.items())},sort_keys=True).encode()
    ).hexdigest()
    return WorldModel(entities,revision,tuple(sorted(conflicts)),len(rows))