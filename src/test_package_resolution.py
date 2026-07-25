import json
import os
import unittest

from test_phase7_helpers import IntelligenceHarness


class PackageResolutionTests(unittest.TestCase):
    def test_workspace_pass_resolves_absolute_and_relative_local_imports(self):
        harness = IntelligenceHarness()
        try:
            package = os.path.join(harness.temp.name, "pkg")
            os.makedirs(package)
            files = {
                "pkg/__init__.py": "",
                "pkg/models.py": "class Record: pass\n",
                "pkg/consumer.py": "from .models import Record\n",
                "app.py": "from pkg import models\n",
            }
            for relative, content in files.items():
                path = os.path.join(harness.temp.name, relative)
                with open(path, "w", encoding="utf-8") as file:
                    file.write(content)

            harness.indexer.reindex_workspace(harness.temp.name)
            harness.indexer.wait_until_idle()

            consumer = harness.graph.related(os.path.join(package, "consumer.py"))[0]
            app = harness.graph.related(os.path.join(harness.temp.name, "app.py"))[0]
            consumer_metadata = json.loads(consumer["metadata"])
            app_metadata = json.loads(app["metadata"])
            self.assertEqual(consumer_metadata["resolved_module"], "pkg.models")
            self.assertEqual(app_metadata["resolved_module"], "pkg.models")
            self.assertEqual(consumer_metadata["resolution"], "local")
        finally:
            harness.close()
