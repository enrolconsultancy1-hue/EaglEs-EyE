import os
import unittest

from test_phase7_helpers import IntelligenceHarness


class SQLiteRecoveryTests(unittest.TestCase):
    def test_failed_transaction_rolls_back_and_database_stays_valid(self):
        harness = IntelligenceHarness()
        try:
            with self.assertRaises(RuntimeError):
                with harness.store.transaction() as connection:
                    connection.execute("INSERT INTO events(event_type, path, payload, created_at) VALUES ('TEST', 'x', '{}', 'now')")
                    raise RuntimeError("simulated interruption")
            self.assertEqual(harness.store.recent_events(), [])
            self.assertEqual(harness.store.integrity_check(), "ok")
        finally:
            harness.close()
