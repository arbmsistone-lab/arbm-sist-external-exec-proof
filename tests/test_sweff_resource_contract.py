from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "sweff-resource-contract.yml"


class SweffResourceContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_official_container_contract_is_pinned(self):
        self.assertIn('REQUIRED_RESERVATION_MIB: \'16384\'', self.text)
        self.assertIn('REQUIRED_LIMIT_MIB: \'32768\'', self.text)
        self.assertIn('mem_limit="32g"', self.text)
        self.assertIn('mem_reservation="16g"', self.text)
        self.assertIn('memswap_limit="32g"', self.text)

    def test_summary_records_both_memory_thresholds(self):
        self.assertIn('requiredReservationMiB', self.text)
        self.assertIn('requiredLimitMiB', self.text)
        self.assertIn('reservationCompatible', self.text)
        self.assertIn('hardLimitCompatible', self.text)
        self.assertIn('officialContainerContract', self.text)


if __name__ == "__main__":
    unittest.main()
