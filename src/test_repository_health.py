import unittest
from test_phase7_helpers import IntelligenceHarness
from services.reflection_service import ReflectionService

class RepositoryHealthTests(unittest.TestCase):
    def test_persists_repository_health_snapshot(self):
        h = IntelligenceHarness()
        try:
            reflection = ReflectionService(h.kernel); reflection.start()
            health = reflection.repository_health(h.documentation.analyze(h.temp.name), h.architecture.analyze())
            self.assertIn("symbols", health)
            self.assertGreaterEqual(h.store.statistics()["reflections"], 2)
        finally: h.close()
