from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping
from .action_ir import ActionIR, ActionKind, TargetRef
from .world_model import WorldModel

@dataclass(frozen=True)
class Mission:
    mission_id: str
    objective: str
    target_entity: str
    desired_state: Mapping[str, Any]
    constraints: tuple[str, ...] = ()

@dataclass(frozen=True)
class Plan:
    mission_id: str
    world_revision: str
    actions: tuple[ActionIR, ...]
    success_conditions: tuple[str, ...]

class HierarchicalPlanner:
    """Deterministic contract planner. Model planners may propose, but this layer validates."""
    def plan(self, mission: Mission, world: WorldModel) -> Plan:
        if not mission.mission_id or not mission.objective.strip():
            raise ValueError("MISSION_IDENTITY_REQUIRED")
        entity=world.require_entity(mission.target_entity)
        changes={k:v for k,v in mission.desired_state.items() if entity.attributes.get(k)!=v}
        if not changes:
            return Plan(mission.mission_id,world.revision,(),("desired_state_already_true",))
        target=TargetRef(entity.entity_id,entity.sources[0] if entity.sources else "world-model",entity.version,
                         {"world_digest":entity.digest})
        actions=[]
        for key,value in sorted(changes.items()):
            actions.append(ActionIR(
                kind=ActionKind.FILE_EDIT if entity.attributes.get("modality")=="file" else ActionKind.TYPE_TEXT,
                target=target,
                payload={"field":key,"text":str(value),"value":value},
                preconditions=(f"entity.version=={entity.version}",f"world.revision=={world.revision}"),
                postconditions=(f"{key}=={value!r}",),
                rollback={"field":key,"value":entity.attributes.get(key)},
                max_attempts=1,
                metadata={"mission_id":mission.mission_id,"objective":mission.objective},
            ))
        for action in actions:
            action.validate()
        return Plan(mission.mission_id,world.revision,tuple(actions),tuple(f"{k}=={v!r}" for k,v in sorted(changes.items())))