#!/usr/bin/env python3
from dataclasses import dataclass, field
from typing import Dict, Set

QUALIFIED="QUALIFIED"

@dataclass
class Route:
    route_id:str
    capability:str
    domain:str
    dependencies:Set[str]=field(default_factory=set)
    state:str=QUALIFIED
    witness_epoch:int=0
    witness_ttl:int=300
    takeover_proven:bool=True
    def counts(self,now:int)->bool:
        return self.state==QUALIFIED and self.takeover_proven and now-self.witness_epoch<=self.witness_ttl

@dataclass
class Mission:
    mission_id:str
    owner:str
    lease_until:int
    fencing_token:int=1
    checkpoint:int=0
    committed_effects:Dict[str,str]=field(default_factory=dict)

    def takeover(self,new_owner:str,now:int):
        if now<=self.lease_until:
            raise RuntimeError("LEASE_ACTIVE")
        self.owner=new_owner; self.fencing_token+=1; self.lease_until=now+30
        return self.fencing_token

    def checkpoint_write(self,owner:str,token:int,step:int):
        if owner!=self.owner or token!=self.fencing_token:
            raise RuntimeError("STALE_FENCE")
        if step<self.checkpoint:
            raise RuntimeError("CHECKPOINT_REGRESSION")
        self.checkpoint=step

    def reconcile_effect(self,key:str,observed_result:str):
        prior=self.committed_effects.get(key)
        if prior is not None and prior!=observed_result:
            raise RuntimeError("IDEMPOTENCY_CONFLICT")
        self.committed_effects[key]=observed_result
        return prior is not None

def independent_domains(routes,capability,now):
    usable=[r for r in routes if r.capability==capability and r.counts(now)]
    # Connected components over complete dependency footprints.  This is
    # intentionally order-independent: transitive shared dependencies collapse
    # nominally different routes into one failure domain.
    footprints=[{r.domain}|set(r.dependencies) for r in usable]
    parent=list(range(len(footprints)))
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]]
            x=parent[x]
        return x
    def union(a,b):
        ra,rb=find(a),find(b)
        if ra!=rb: parent[rb]=ra
    for i in range(len(footprints)):
        for j in range(i):
            if footprints[i] & footprints[j]:
                union(i,j)
    return len({find(i) for i in range(len(footprints))})

def survives(routes,capability,now,lost_domains,min_remaining=1):
    alive=[r for r in routes if r.domain not in lost_domains and not (r.dependencies & lost_domains)]
    return independent_domains(alive,capability,now)>=min_remaining
