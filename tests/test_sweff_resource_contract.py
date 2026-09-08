from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "sweff-resource-contract.yml"


class SweffResourceContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_official_contract_is_pinned(self):
        for expected in (
            'mem_limit="32g"', 'mem_reservation="16g"',
            'memswap_limit="32g"', 'oom_kill_disable=True',
            'vcpus_per_worker=4', 'threads_per_core=2', 'reserve_cores=4',
        ):
            self.assertIn(expected, self.text)

    def test_v3_uses_runtime_and_topology_not_host_32g(self):
        self.assertIn("arbm-sweff-resource-contract-v3", self.text)
        self.assertIn("physicalCoresDiscovered", self.text)
        self.assertIn("eligiblePhysicalCores", self.text)
        self.assertIn("dockerMemoryEnvelopeAccepted", self.text)
        self.assertIn("oomKillDisableEffective", self.text)
        self.assertIn("BLOCKED_CPU_TOPOLOGY", self.text)
        self.assertNotIn("observed_mib >= limit_mib", self.text)


if __name__ == "__main__":
    unittest.main()
