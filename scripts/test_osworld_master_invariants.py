import re
import unittest
from pathlib import Path
import osworld_free_mesh_shim as shim
import osworld_local_vlm as local_vlm

ROOT=Path(__file__).resolve().parents[1]
MASTER='chatgpt/arbm-agent-elite-v2-20260914'
FORBIDDEN=('paid-bounded','PAID_BOUNDED','openrouter_paid','REAL_PAID_MODEL_RESPONSE','--paid')

class MasterInvariantTests(unittest.TestCase):
    def test_endpoint_and_shim_build_identity_match(self):
        endpoint=(ROOT/'endpoint/index.ts').read_text()
        build=re.search(r'const BUILD = "([^"]+)"',endpoint).group(1)
        self.assertEqual(build,shim.EXPECTED_BUILD)
        self.assertEqual(build,'arbm-osworld-v32-master-20260914')

    def test_only_master_oidc_branch_is_executable(self):
        endpoint=(ROOT/'endpoint/index.ts').read_text()
        self.assertIn('refs/heads/'+MASTER,endpoint)
        for stale in ('chatgpt/osworld-v32-rescue-20260912','codex/osworld-close-','free-capacity-osworld-v31'):
            self.assertNotIn(stale,endpoint)

    def test_zero_spend_runtime_has_no_paid_or_mistral_path(self):
        paths=[ROOT/'endpoint/index.ts']+[p for p in (ROOT/'scripts').glob('*.py') if not p.name.startswith('test_')]+list((ROOT/'.github/workflows').glob('*.yml'))
        text='\n'.join(p.read_text(encoding='utf-8-sig') for p in paths)
        for needle in FORBIDDEN:self.assertNotIn(needle,text)
        self.assertNotIn('api.mistral.ai',text)
        self.assertNotIn('mistral-small-latest',text)

    def test_official_workflow_is_master_only_and_dependencies_are_pinned(self):
        workflow=(ROOT/'.github/workflows/osworld-v32-official-18.yml').read_text()
        self.assertIn('- '+MASTER,workflow)
        self.assertNotIn('chatgpt/osworld-v32-rescue-20260912',workflow)
        self.assertIn("'safetensors==0.8.0'",workflow)
        for wf in (ROOT/'.github/workflows').glob('*.yml'):
            for use in re.findall(r'uses:\s*([^\s#]+)',wf.read_text()):
                if use.startswith('actions/'):
                    self.assertRegex(use,r'@[0-9a-f]{40}$',msg=str(wf)+': '+use)

    def test_v31_workflows_are_archived_not_executable(self):
        names={p.name for p in (ROOT/'.github/workflows').glob('*.yml')}
        self.assertNotIn('osworld-v31-official-108.yml',names)
        self.assertNotIn('osworld-sovereign-e2e.yml',names)
        self.assertTrue((ROOT/'reports/historical-workflows/osworld-v31-official-108.yml').is_file())
        self.assertTrue((ROOT/'reports/historical-workflows/osworld-sovereign-e2e-v31.yml').is_file())

    def test_local_vlm_model_revision_is_fixed(self):
        self.assertEqual(local_vlm.MODEL,'HuggingFaceTB/SmolVLM-256M-Instruct')
        self.assertRegex(local_vlm.MODEL_REVISION,r'^[0-9a-f]{40}$')

    def test_preflight_independent_failover_excludes_groq_mesh(self):
        text=(ROOT/'scripts/osworld_v32_preflight.py').read_text()
        self.assertIn('shim.FREE_ROUTE.call(failover_body',text)
        self.assertIn('LOCAL_VLM_ROUTE.call(failover_body',text)
        self.assertNotIn('request_mesh(failover_body)',text)
        self.assertIn('Groq excluded from this proof',text)

    def test_openai_compatible_response_reports_v32_model(self):
        text=(ROOT/'scripts/osworld_free_mesh_shim.py').read_text()
        self.assertIn("'id':'arbm-osworld-v32-isolated'",text)
        self.assertIn("'model':'gpt-arbm-osworld-v32-isolated'",text)

if __name__=='__main__':unittest.main()
