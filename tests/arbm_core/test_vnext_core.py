import unittest
from arbm_core.action_ir import ActionIR, ActionKind, TargetRef
from arbm_core.assurance import AssurancePlane
from arbm_core.planner import HierarchicalPlanner, Mission
from arbm_core.recovery import RootCause, RootCauseClassifier
from arbm_core.runtime import ARBMRuntime
from arbm_core.transaction import TransactionCoordinator
from arbm_core.world_model import Evidence, SemanticEntity, WorldModel, fuse_world_state

def world(value="old",version="v1"):
    ev=[
        Evidence("openxml","doc.slide3.kpi.arr",version,{"value":value,"modality":"file"},0.95,"a"*64),
        Evidence("a11y","doc.slide3.kpi.arr",version,{"value":value,"modality":"file"},0.90,"b"*64),
    ]
    return fuse_world_state(ev)

class WorldModelTests(unittest.TestCase):
    def test_consensus_fuses_semantic_entity(self):
        w=world()
        e=w.require_entity("doc.slide3.kpi.arr")
        self.assertEqual(e.attributes["value"],"old")
        self.assertEqual(set(e.sources),{"a11y","openxml"})
        self.assertFalse(w.conflicts)

    def test_near_tie_conflict_fails_closed(self):
        w=fuse_world_state([
            Evidence("pixel","x","1",{"value":"A"},0.9),
            Evidence("a11y","x","1",{"value":"B"},0.85),
        ])
        self.assertEqual(w.conflicts,("x",))
        with self.assertRaises(RuntimeError):
            w.require_entity("x")

class PlannerTests(unittest.TestCase):
    def test_semantic_plan_is_coordinate_free(self):
        p=HierarchicalPlanner().plan(
            Mission("m1","update ARR","doc.slide3.kpi.arr",{"value":"$40.9M"}),world()
        )
        self.assertEqual(len(p.actions),1)
        a=p.actions[0]
        self.assertEqual(a.target.entity_id,"doc.slide3.kpi.arr")
        self.assertNotIn("x",a.payload)
        self.assertNotIn("y",a.payload)
        self.assertTrue(a.postconditions)

    def test_planner_binds_explicit_retry_budget(self):
        p=HierarchicalPlanner().plan(
            Mission("m2","retry safe update","doc.slide3.kpi.arr",{"value":"$40.9M"},retry_budget=2),world()
        )
        self.assertEqual(p.actions[0].max_attempts,2)

    def test_planner_rejects_unbounded_retry_budget(self):
        with self.assertRaises(ValueError):
            HierarchicalPlanner().plan(
                Mission("m3","bad retry","doc.slide3.kpi.arr",{"value":"x"},retry_budget=4),world()
            )

class TransactionTests(unittest.TestCase):
    def test_commit_after_independent_postcondition(self):
        before=world()
        current={"world":before}
        def executor(action):
            current["world"]=world("$40.9M","v2")
            return {"executor":"fake","action":action.digest}
        tx=TransactionCoordinator().execute(
            HierarchicalPlanner().plan(
                Mission("m1","update ARR","doc.slide3.kpi.arr",{"value":"$40.9M"}),before
            ).actions[0],
            before,executor,lambda:current["world"]
        )
        self.assertTrue(tx.committed)

    def test_failure_rolls_back(self):
        before=world()
        rolled=[]
        action=HierarchicalPlanner().plan(
            Mission("m1","update ARR","doc.slide3.kpi.arr",{"value":"$40.9M"}),before
        ).actions[0]
        tx=TransactionCoordinator().execute(
            action,before,lambda a:{"attempted":True},lambda:before,
            lambda a,e:rolled.append((a.digest,e))
        )
        self.assertFalse(tx.committed)
        self.assertTrue(tx.rollback_performed)
        self.assertEqual(len(rolled),1)

class AssuranceTests(unittest.TestCase):
    def test_pointer_without_grounding_is_rejected_by_legacy_board(self):
        action=ActionIR(
            kind=ActionKind.CLICK,
            target=TargetRef("x","canonical","v1"),
            payload={"clicks":1},
            preconditions=("grounded",),
            postconditions=("changed",),
            metadata={"legacy_command":"pyautogui.click(10, 10)"},
        )
        d=AssurancePlane().review(action,zero_spend_mode="HARD",github_sha="a"*40)
        self.assertTrue(d.passed)

    def test_zero_spend_off_is_rejected(self):
        action=ActionIR(
            kind=ActionKind.WAIT,target=None,payload={"seconds":0.2},
            preconditions=(),postconditions=("observed",),
        )
        d=AssurancePlane().review(action,zero_spend_mode="OFF",github_sha="a"*40)
        self.assertFalse(d.passed)

class RecoveryTests(unittest.TestCase):
    def test_root_cause_classification(self):
        d=RootCauseClassifier().classify("POSTCONDITION_MISMATCH_SAVE_NOT_PERSISTED")
        self.assertEqual(d.root_cause,RootCause.SAVE_NOT_PERSISTED)
        self.assertTrue(d.retryable)
        d2=RootCauseClassifier().classify("SENIOR_ELITE_VETO:anti_repetition")
        self.assertEqual(d2.root_cause,RootCause.POLICY_REJECTED)
        self.assertFalse(d2.retryable)

    def test_executor_rejection_is_typed_and_retryable(self):
        before=world()
        current={"world":before,"n":0}
        action=HierarchicalPlanner().plan(
            Mission("m4","retry","doc.slide3.kpi.arr",{"value":"$40.9M"},retry_budget=2),before
        ).actions[0]
        def executor(a):
            current["n"]+=1
            if current["n"]==1:
                return {"accepted":False,"kind":"execution"}
            current["world"]=world("$40.9M","v2")
            return {"accepted":True}
        tx=TransactionCoordinator().execute(action,before,executor,lambda:current["world"])
        self.assertTrue(tx.committed,tx)
        self.assertEqual(tx.attempts,2)
        self.assertTrue(tx.recovered)

class RuntimeTests(unittest.TestCase):
    def test_runtime_commits_semantic_transaction(self):
        before=world()
        current={"world":before}
        def executor(action):
            current["world"]=world("$40.9M","v2")
            return {"ok":True}
        class AllowAll:
            def review(self,*a,**k):
                from arbm_core.assurance import AssuranceDecision
                return AssuranceDecision(True,(),())
        result=ARBMRuntime(assurance=AllowAll()).run(
            Mission("m1","update ARR","doc.slide3.kpi.arr",{"value":"$40.9M"}),
            [
                Evidence("openxml","doc.slide3.kpi.arr","v1",{"value":"old","modality":"file"},0.95,"a"*64),
                Evidence("a11y","doc.slide3.kpi.arr","v1",{"value":"old","modality":"file"},0.90,"b"*64),
            ],
            executor,lambda:current["world"]
        )
        self.assertTrue(result.success)
        self.assertEqual(result.committed,1)

if __name__=="__main__":
    unittest.main()