import unittest
from datetime import datetime, timezone

from scripts.dora_metrics import summarize


class DoraMetricsTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 10, 12, tzinfo=timezone.utc)

    def test_no_deployments_is_not_fabricated_data(self):
        report = summarize([], self.now)
        self.assertEqual(report["metrics"]["deployment_frequency"]["successful_deployments"], 0)
        self.assertEqual(report["metrics"]["deployment_frequency"]["status"], "INSUFFICIENT_DATA")
        self.assertIsNone(report["metrics"]["change_failure_rate"]["rate"])
        self.assertIsNone(report["metrics"]["lead_time_for_changes"]["median_hours"])

    def test_computes_frequency_failure_rate_lead_and_restore(self):
        deployments = [
            {"id": 1, "state": "failure", "created_at": "2026-10-08T10:00:00+00:00",
             "status_at": "2026-10-08T10:00:00+00:00", "commit_at": "2026-10-08T09:00:00+00:00"},
            {"id": 2, "state": "success", "created_at": "2026-10-08T12:00:00+00:00",
             "status_at": "2026-10-08T12:00:00+00:00", "commit_at": "2026-10-08T09:00:00+00:00"},
            {"id": 3, "state": "success", "created_at": "2026-10-09T12:00:00+00:00",
             "status_at": "2026-10-09T12:00:00+00:00", "commit_at": "2026-10-09T10:00:00+00:00"},
        ]
        report = summarize(deployments, self.now)
        metrics = report["metrics"]
        self.assertEqual(metrics["deployment_frequency"]["successful_deployments"], 2)
        self.assertAlmostEqual(metrics["change_failure_rate"]["rate"], 1 / 3)
        self.assertEqual(metrics["lead_time_for_changes"]["sample_size"], 2)
        self.assertEqual(metrics["time_to_restore"]["median_hours"], 2.0)
        self.assertEqual(metrics["time_to_restore"]["status"], "PROXY_MEASURED")

    def test_pending_deployments_are_not_in_failure_rate_denominator(self):
        report = summarize([
            {"id": 1, "state": "pending", "created_at": "2026-10-08T10:00:00+00:00",
             "status_at": "2026-10-08T10:00:00+00:00", "commit_at": None},
        ], self.now)
        self.assertIsNone(report["metrics"]["change_failure_rate"]["rate"])
        self.assertEqual(report["sample"]["pending_or_other"], 1)


if __name__ == "__main__":
    unittest.main()
