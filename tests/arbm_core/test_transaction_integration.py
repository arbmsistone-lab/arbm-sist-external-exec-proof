import unittest
from arbm_core.action_ir import ActionIR, ActionKind, TargetRef
from arbm_core.executor_adapter import LegacyExecutorAdapter, LegacyObservationAdapter
from arbm_core.legacy_bridge import world_from_legacy_observation
from arbm_core.transaction import TransactionCoordinator

def obs(value, sha):
    return {
        "deck_file":{"sha256":sha},
        "deck_slide_shapes":{"3":[
            {"id":-13001003,"kind":"table-cell","name":"Table 12#r1c2",
             "text":value,"geometry":{"x":900,"y":400,"w":180,"h":70}}
        ]}
    }

class TransactionIntegrationTests(unittest.TestCase):
    def test_action_ir_to_grounded_dispatch_to_verified_commit(self):
        before_obs=obs("$42.8M","a"*64)
        after_obs=obs("$40.9M","b"*64)
        before=world_from_legacy_observation(before_obs)
        current={"obs":before_obs}
        dispatched=[]

        target=TargetRef(
            "deck.slide3.table-cell.Table 12#r1c2",
            "accessibility",
            "a"*64,
            {"label":"ARR H2","role":"entry"}
        )
        action=ActionIR(
            ActionKind.TYPE_TEXT,target,
            {"text":"$40.9M"},
            ("target grounded",),
            ("text=='$40.9M'",),
            rollback={"text":"$42.8M"},
            max_attempts=1,
            metadata={"plan":"replace ARR H2 value"},
        )

        observation_text="entry\tARR H2\t\t\t\t900,400\t180x70"
        adapter=LegacyExecutorAdapter(
            active_application="WPS Presentation",
            observation_text=observation_text
        )

        def dispatch(legacy):
            dispatched.append(legacy)
            current["obs"]=after_obs
            return {"transport":"osworld","accepted":True}

        executor=adapter.executor(dispatch)
        observer=LegacyObservationAdapter(lambda:current["obs"]).observe_world

        tx=TransactionCoordinator().execute(action,before,executor,observer)
        self.assertTrue(tx.committed,tx)
        self.assertEqual(tx.attempts,1)
        self.assertEqual(dispatched[0]["action"],"exec")
        self.assertIn("$40.9M",dispatched[0]["command"])
        self.assertEqual(tx.post.code,"POSTCONDITION_PASS")

    def test_failed_postcondition_rolls_back_after_real_compilation(self):
        before_obs=obs("$42.8M","a"*64)
        current={"obs":before_obs}
        rolled=[]
        target=TargetRef(
            "deck.slide3.table-cell.Table 12#r1c2",
            "accessibility",
            "a"*64,
            {"label":"ARR H2","role":"entry"}
        )
        action=ActionIR(
            ActionKind.TYPE_TEXT,target,
            {"text":"$40.9M"},
            ("target grounded",),
            ("text=='$40.9M'",),
            rollback={"text":"$42.8M"},
            max_attempts=1,
            metadata={"plan":"replace ARR H2 value"},
        )
        adapter=LegacyExecutorAdapter(
            active_application="WPS Presentation",
            observation_text="entry\tARR H2\t\t\t\t900,400\t180x70"
        )
        tx=TransactionCoordinator().execute(
            action,
            world_from_legacy_observation(before_obs),
            adapter.executor(lambda legacy:{"accepted":True}),
            LegacyObservationAdapter(lambda:current["obs"]).observe_world,
            lambda a,e:rolled.append((a.digest,e)),
        )
        self.assertFalse(tx.committed)
        self.assertTrue(tx.rollback_performed)
        self.assertEqual(len(rolled),1)

if __name__=="__main__":
    unittest.main()