import os
import unittest

from services.workspace_observer_service import WorkspaceObserverService
from test_phase7_helpers import IntelligenceHarness


class WorkspaceObserverServiceTests(unittest.TestCase):
    def setUp(self):
        self.harness = IntelligenceHarness()
        self.observer = WorkspaceObserverService(self.harness.kernel)
        self.harness.kernel.register_service(self.observer)
        self.observer.start()

    def tearDown(self):
        self.observer.stop()
        self.harness.close()

    def test_registers_multiple_isolated_workspace_identities(self):
        first_path = os.path.join(self.harness.temp.name, "first")
        second_path = os.path.join(self.harness.temp.name, "second")
        os.makedirs(first_path)
        os.makedirs(second_path)

        first = self.observer.register_workspace(first_path, {"label": "first"})
        second = self.observer.register_workspace(second_path, {"label": "second"})

        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(first["metadata"]["label"], "first")
        self.assertEqual(second["metadata"]["label"], "second")
        self.assertEqual([item["path"] for item in self.observer.workspaces()], [first_path, second_path])
        self.assertEqual(self.harness.store.statistics()["workspaces"], 2)

    def test_registration_is_stable_and_does_not_change_existing_events(self):
        path = os.path.join(self.harness.temp.name, "workspace")
        os.makedirs(path)
        self.harness.store.record_event("LEGACY_EVENT", path, {"source": "existing"})

        first = self.observer.register_workspace(path)
        second = self.observer.register_workspace(path)

        self.assertEqual(first["id"], second["id"])
        event = self.harness.store.recent_events()[0]
        self.assertEqual(event["event_type"], "LEGACY_EVENT")
        self.assertIsNone(event["workspace_id"])
        self.assertIsNone(event["session_id"])

    def test_rejects_a_nonexistent_workspace(self):
        with self.assertRaises(ValueError):
            self.observer.register_workspace(os.path.join(self.harness.temp.name, "missing"))
