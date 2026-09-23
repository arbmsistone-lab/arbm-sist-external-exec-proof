import unittest
from arbm_core.legacy_bridge import evidence_from_legacy_observation, world_from_legacy_observation

class LegacyBridgeTests(unittest.TestCase):
    def test_observation_becomes_semantic_entities(self):
        obs={
            "deck_file":{"sha256":"a"*64},
            "deck_slide_shapes":{"3":[
                {"id":-13001003,"kind":"table-cell","name":"Table 12#r1c2",
                 "text":"$40.9M","geometry":{"x":1,"y":2,"w":3,"h":4}}
            ]}
        }
        rows=evidence_from_legacy_observation(obs)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0].entity_id,"deck.slide3.table-cell.Table 12#r1c2")
        world=world_from_legacy_observation(obs)
        entity=world.require_entity("deck.slide3.table-cell.Table 12#r1c2")
        self.assertEqual(entity.attributes["text"],"$40.9M")
        self.assertEqual(entity.attributes["slide"],3)
        self.assertEqual(entity.version,"a"*64)

    def test_missing_shapes_yields_empty_conflict_free_world(self):
        world=world_from_legacy_observation({"deck_file":{"sha256":"b"*64}})
        self.assertEqual(world.entities,{})
        self.assertEqual(world.conflicts,())

if __name__=="__main__":
    unittest.main()