import json,tempfile,unittest
from pathlib import Path
from arbm_core.osworld_external_catalog import load_catalog,EXPECTED_TASKS

class ExternalCatalogTests(unittest.TestCase):
    def test_expected_official_count_contract(self):
        self.assertEqual(EXPECTED_TASKS,369)

    def test_loader_preserves_ids_and_instruction(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"evaluation_examples/examples/chrome").mkdir(parents=True)
            meta={"chrome":["abc"]}
            (root/"evaluation_examples/test_all.json").write_text(json.dumps(meta))
            (root/"evaluation_examples/examples/chrome/abc.json").write_text(json.dumps({"instruction":"Do it"}))
            import arbm_core.osworld_external_catalog as m
            old=m.EXPECTED_TASKS
            m.EXPECTED_TASKS=1
            try:
                rows=load_catalog(root)
            finally:
                m.EXPECTED_TASKS=old
            self.assertEqual(rows[0]["task_id"],"chrome:abc")
            self.assertEqual(rows[0]["instruction"],"Do it")
            self.assertEqual(len(rows[0]["config_sha256"]),64)
if __name__=="__main__":
    unittest.main()