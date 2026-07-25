import os
import unittest
from test_phase7_helpers import IntelligenceHarness

class SymbolIndexerTests(unittest.TestCase):
    def test_extracts_versioned_nested_and_decorated_symbols(self):
        h = IntelligenceHarness()
        try:
            path = os.path.join(h.temp.name, "symbols.py")
            with open(path, "w", encoding="utf-8") as file: file.write("from dataclasses import dataclass\n@dataclass\nclass Outer:\n    VALUE = 1\n    @property\n    def value(self): return self.VALUE\n    class Inner: pass\nasync def work(x): return x\n")
            h.indexer.reindex_path(path); h.indexer.wait_until_idle()
            symbols = h.store.find_symbols("", 100)
            kinds = {item["kind"] for item in symbols}
            self.assertTrue({"module", "dataclass", "property", "class", "async_function", "constant"}.issubset(kinds))
            self.assertTrue(all("symbol_id" in item for item in symbols))
        finally: h.close()
