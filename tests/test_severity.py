import unittest

from ml.src.severity import estimate_severity


class TestSeverity(unittest.TestCase):
    def test_default_severity_by_issue_type(self):
        expected = {
            "pothole": "medium",
            "garbage": "low",
            "streetlight": "medium",
            "water_leakage": "medium",
            "drainage": "medium",
        }

        for issue, severity in expected.items():
            with self.subTest(issue=issue):
                result = estimate_severity(issue)
                self.assertEqual(result["severity"], severity)
                self.assertTrue(result["requires_human_review"])

    def test_traffic_block_escalates_to_high(self):
        result = estimate_severity(
            "water_leakage", {"blocks_traffic": True}
        )
        self.assertEqual(result["severity"], "high")

    def test_immediate_danger_escalates_to_critical(self):
        result = estimate_severity(
            "drainage", {"immediate_danger": True}
        )
        self.assertEqual(result["severity"], "critical")

    def test_emergency_access_takes_priority(self):
        result = estimate_severity(
            "pothole", {"blocks_emergency_access": True}
        )
        self.assertEqual(result["severity"], "critical")

    def test_multiple_households_escalates_to_high(self):
        result = estimate_severity(
            "streetlight", {"affects_multiple_households": True}
        )
        self.assertEqual(result["severity"], "high")

    def test_invalid_issue_is_rejected(self):
        with self.assertRaises(ValueError):
            estimate_severity("noise")

    def test_non_boolean_evidence_is_rejected(self):
        with self.assertRaises(TypeError):
            estimate_severity("pothole", {"immediate_danger": "yes"})

    def test_invalid_evidence_type_is_rejected(self):
        with self.assertRaises(TypeError):
            estimate_severity("pothole", ["immediate_danger"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
