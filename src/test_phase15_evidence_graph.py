"""Phase 15 — Unified Evidence & Knowledge Graph tests."""

import unittest
import warnings

from core.event_bus import EventBus
from connectors.evidence_bus import EvidenceBus
from connectors.events import CONNECTOR_EVIDENCE, CONNECTOR_OBSERVATION
from connectors.models import (
    Source, RawPayload, Observation, Evidence as EvidenceModel,
    NormalizedPayload, TraceInformation, Relationship,
)


# ---------------------------------------------------------------------------
# Dummy kernel for testing
# ---------------------------------------------------------------------------

class DummyKernel:
    def __init__(self, config=None):
        self.services = {}
        self.event_bus = EventBus()
        self._config = config or {}

    def register_service(self, s):
        self.services[s.name] = s

    def get_service(self, name):
        return self.services.get(name)

    def get_config(self):
        return self._config

    def set_config(self, cfg):
        self._config = cfg


class DummyStore:
    name = "KnowledgeStoreService"

    def __init__(self):
        self.events = []
        self.relationships = []

    def record_event(self, event_type, path, payload, workspace_id=None, session_id=None):
        self.events.append({
            "event_type": event_type, "path": path, "payload": payload,
            "workspace_id": workspace_id, "session_id": session_id,
        })

    def add_relationship(self, source, target, relation, metadata=None):
        self.relationships.append({
            "source": source, "target": target, "relation": relation,
            "metadata": metadata,
        })

    def transaction(self):
        return _DummyConnection()

    def get_document(self, path, include_chunks=False):
        return None


class _DummyConnection:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, *args, **kwargs):
        pass


class DummyManager:
    def __init__(self):
        self.evidence_bus = EvidenceBus()
        self._registry = _DummyRegistry()

    def get_evidence_bus(self):
        return self.evidence_bus

    def get_connector(self, cid):
        from connectors.plugins.mock_connector import MockConnector
        c = MockConnector()
        c.connect()
        return c


class _DummyRegistry:
    def __init__(self):
        self._connectors = {}

    def register(self, connector, manifest=None):
        self._connectors[connector.id] = connector
        return connector.id

    def get(self, connector_id):
        return self._connectors.get(connector_id)

    def has(self, connector_id):
        return connector_id in self._connectors


class DummyConnectorService:
    def __init__(self):
        self._manager = DummyManager()

    def get_manager(self):
        return self._manager


class DummyKnowledgeGraph:
    def __init__(self):
        self.evidence_log = []

    def ingest_connector_evidence(self, connector_id, evidence_list):
        self.evidence_log.append((connector_id, evidence_list))
        return {"imported": len(evidence_list), "connector_id": connector_id}


# ---------------------------------------------------------------------------
# EventBus — hardening
# ---------------------------------------------------------------------------

class Phase15EventBusTests(unittest.TestCase):
    def test_subscribe_returns_token(self):
        bus = EventBus()
        token = bus.subscribe("TEST", lambda d: None)
        self.assertIsNotNone(token)

    def test_unsubscribe_removes_listener(self):
        bus = EventBus()
        received = []
        token = bus.subscribe("TEST", lambda d: received.append(d))
        bus.publish("TEST", "data1")
        self.assertEqual(len(received), 1)
        bus.unsubscribe(token)
        bus.publish("TEST", "data2")
        self.assertEqual(len(received), 1)

    def test_error_isolation(self):
        bus = EventBus()
        good = []
        def failing(data):
            raise ValueError("fail")
        def good_cb(data):
            good.append(data)
        bus.subscribe("TEST", failing)
        bus.subscribe("TEST", good_cb)
        bus.publish("TEST", "data")
        self.assertEqual(len(good), 1)

    def test_unsubscribe_nonexistent_token(self):
        bus = EventBus()
        bus.unsubscribe(99999)

    def test_multiple_events_same_listener(self):
        bus = EventBus()
        received = []
        token = bus.subscribe("A", lambda d: received.append(("A", d)))
        bus.subscribe("B", lambda d: received.append(("B", d)))
        bus.publish("A", 1)
        bus.publish("B", 2)
        bus.unsubscribe(token)
        bus.publish("A", 3)
        self.assertEqual(len(received), 2)


# ---------------------------------------------------------------------------
# EvidenceBus
# ---------------------------------------------------------------------------

class Phase15EvidenceBusTests(unittest.TestCase):
    def test_publish_evidence(self):
        bus = EventBus()
        eb = EvidenceBus(event_bus=bus)
        events = []
        bus.subscribe(CONNECTOR_EVIDENCE, lambda d: events.append(d))
        eb.publish_evidence("test_conn", [{"id": "ev1"}])
        self.assertEqual(len(events), 1)

    def test_publish_observation(self):
        bus = EventBus()
        eb = EvidenceBus(event_bus=bus)
        events = []
        bus.subscribe(CONNECTOR_OBSERVATION, lambda d: events.append(d))
        eb.publish_observation("test_conn", [{"id": "obs1"}])
        self.assertEqual(len(events), 1)

    def test_subscribe_callback(self):
        eb = EvidenceBus()
        received = []
        eb.subscribe(lambda cid, ev_list: received.append((cid, ev_list)))
        eb.publish_evidence("test", [{"id": "ev1"}])
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0][0], "test")

    def test_unsubscribe_callback(self):
        eb = EvidenceBus()
        received = []
        def cb(cid, ev_list):
            received.append((cid, ev_list))
        eb.subscribe(cb)
        eb.unsubscribe(cb)
        eb.publish_evidence("test", [{"id": "ev1"}])
        self.assertEqual(len(received), 0)

    def test_set_event_bus(self):
        eb = EvidenceBus()
        bus = EventBus()
        eb.set_event_bus(bus)
        events = []
        bus.subscribe(CONNECTOR_EVIDENCE, lambda d: events.append(d))
        eb.publish_evidence("test", [{"id": "ev1"}])
        self.assertEqual(len(events), 1)


# ---------------------------------------------------------------------------
# EvidenceIngestionService
# ---------------------------------------------------------------------------

class Phase15IngestionTests(unittest.TestCase):
    def setUp(self):
        self.kernel = DummyKernel()
        store = DummyStore()
        self.kernel.services["KnowledgeStoreService"] = store
        self.kernel.services["ConnectorService"] = DummyConnectorService()
        from services.evidence_ingestion_service import EvidenceIngestionService
        self.svc = EvidenceIngestionService(self.kernel)

    def test_start_requires_store(self):
        bare = DummyKernel()
        from services.evidence_ingestion_service import EvidenceIngestionService
        svc = EvidenceIngestionService(bare)
        with self.assertRaises(RuntimeError):
            svc.start()

    def test_start_requires_connector(self):
        bare = DummyKernel()
        bare.services["KnowledgeStoreService"] = DummyStore()
        from services.evidence_ingestion_service import EvidenceIngestionService
        svc = EvidenceIngestionService(bare)
        with self.assertRaises(RuntimeError):
            svc.start()

    def test_ingest_evidence(self):
        self.svc.start()
        source = Source.create(type_="test")
        raw = RawPayload.from_text("test data")
        obs = Observation.create(type_="test_event", source=source, raw=raw)
        norm = NormalizedPayload.structured({"data": "test"})
        trace = TraceInformation("test_conn", "1.0", ["observe", "emit"])
        evidence = EvidenceModel.create(observation=obs, normalized=norm, trace=trace)
        result = self.svc.ingest("test_conn", [evidence])
        self.assertEqual(result["ingested"], 1)
        self.assertGreater(result["total"], 0)

    def test_get_stats(self):
        self.svc.start()
        stats = self.svc.get_stats()
        self.assertEqual(stats["ingested_count"], 0)

    def test_stop_cleanup(self):
        self.svc.start()
        self.svc.stop()


# ---------------------------------------------------------------------------
# GitObserverService deprecation
# ---------------------------------------------------------------------------

class Phase15GitObserverDeprecationTests(unittest.TestCase):
    def test_deprecation_warning(self):
        kernel = DummyKernel()
        kernel.services["ConnectorService"] = DummyConnectorService()
        from services.git_observer_service import GitObserverService
        svc = GitObserverService(kernel)
        svc.start()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = svc.observe("/tmp")
            self.assertTrue(len(w) >= 1)
            self.assertTrue(any(
                "deprecated" in str(msg.message).lower() for msg in w
            ))


# ---------------------------------------------------------------------------
# EngineeringEvidenceService deprecation
# ---------------------------------------------------------------------------

class Phase15EngineeringEvidenceDeprecationTests(unittest.TestCase):
    def test_deprecation_warning_on_record(self):
        kernel = DummyKernel()
        store = DummyStore()
        kernel.services["KnowledgeStoreService"] = store
        from services.engineering_evidence_service import EngineeringEvidenceService
        svc = EngineeringEvidenceService(kernel)
        svc.start()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            svc.record_git("/tmp", "snapshot")
            self.assertTrue(len(w) >= 1)
            self.assertTrue(any(
                "deprecated" in str(msg.message).lower() for msg in w
            ))


# ---------------------------------------------------------------------------
# ProcessObserverService deprecation
# ---------------------------------------------------------------------------

class Phase15ProcessObserverDeprecationTests(unittest.TestCase):
    def test_deprecation_warning(self):
        kernel = DummyKernel()
        store = DummyStore()
        kernel.services["KnowledgeStoreService"] = store
        from services.engineering_evidence_service import EngineeringEvidenceService
        eng = EngineeringEvidenceService(kernel)
        eng.start()
        kernel.services["EngineeringEvidenceService"] = eng
        from services.process_observer_service import ProcessObserverService
        svc = ProcessObserverService(kernel)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            svc.start()
            self.assertTrue(len(w) >= 1)


# ---------------------------------------------------------------------------
# KnowledgeGraphService connector evidence extension
# ---------------------------------------------------------------------------

class Phase15KnowledgeGraphEvidenceTests(unittest.TestCase):
    def test_ingest_connector_evidence(self):
        kg = DummyKnowledgeGraph()
        source = Source.create(type_="test")
        raw = RawPayload.from_text("data")
        obs = Observation.create(type_="test", source=source, raw=raw)
        norm = NormalizedPayload.structured({"data": "test"})
        trace = TraceInformation("c1", "1.0", ["observe", "emit"])
        evidence = EvidenceModel.create(observation=obs, normalized=norm, trace=trace)
        result = kg.ingest_connector_evidence("c1", [evidence])
        self.assertEqual(result["imported"], 1)
        self.assertEqual(result["connector_id"], "c1")

    def test_ingest_with_relationships(self):
        kg = DummyKnowledgeGraph()
        source = Source.create(type_="test")
        raw = RawPayload.from_text("data")
        obs = Observation.create(type_="test", source=source, raw=raw)
        norm = NormalizedPayload.structured({"data": "test"})
        trace = TraceInformation("c1", "1.0", ["observe", "emit"])
        rel = Relationship(source_id="s1", target_id="t1", type="depends_on")
        evidence = EvidenceModel.create(
            observation=obs, normalized=norm, trace=trace,
            relationships=[rel],
        )
        result = kg.ingest_connector_evidence("c1", [evidence])
        self.assertEqual(result["imported"], 1)


# ---------------------------------------------------------------------------
# Evidence bus integration with ConnectorManager
# ---------------------------------------------------------------------------

class Phase15EvidencePipelineIntegrationTests(unittest.TestCase):
    def test_evidence_bus_received_by_ingestion(self):
        from connectors.connector_manager import ConnectorManager
        bus = EventBus()
        manager = ConnectorManager(auto_discover=False, event_bus=bus)
        manager.start()
        from connectors.plugins.mock_connector import MockConnector
        mc = MockConnector()
        mc.connect()
        manager._registry.register(mc)
        evidence_list = manager.collect_evidence("mock")
        self.assertGreater(len(evidence_list), 0)
        manager.stop()

    def test_evidence_flows_through_bus(self):
        eb = EvidenceBus()
        received = []
        eb.subscribe(lambda cid, ev_list: received.append((cid, ev_list)))
        source = Source.create(type_="test")
        raw = RawPayload.from_text("data")
        obs = Observation.create(type_="test", source=source, raw=raw)
        norm = NormalizedPayload.structured({"data": "test"})
        trace = TraceInformation("c1", "1.0", ["observe", "emit"])
        evidence = EvidenceModel.create(observation=obs, normalized=norm, trace=trace)
        eb.publish_evidence("c1", [evidence])
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0][0], "c1")


# ---------------------------------------------------------------------------
# Pipeline integration
# ---------------------------------------------------------------------------

class Phase15PipelineCompleteTests(unittest.TestCase):
    def test_pipeline_connector_to_ingestion(self):
        from connectors.connector_manager import ConnectorManager
        from services.evidence_ingestion_service import EvidenceIngestionService

        kernel = DummyKernel()
        store = DummyStore()
        kernel.services["KnowledgeStoreService"] = store

        manager = ConnectorManager(auto_discover=False)
        manager.start()
        from connectors.plugins.mock_connector import MockConnector
        mc = MockConnector()
        mc.connect()
        manager._registry.register(mc)

        evidence_list = manager.collect_evidence("mock")
        self.assertGreater(len(evidence_list), 0)
        manager.stop()

    def test_full_pipeline_event_in_store(self):
        from connectors.connector_manager import ConnectorManager

        bus = EventBus()
        manager = ConnectorManager(auto_discover=False, event_bus=bus)
        manager.start()
        from connectors.plugins.mock_connector import MockConnector
        mc = MockConnector()
        mc.connect()
        manager._registry.register(mc)

        evidence = manager.collect_evidence("mock")
        self.assertGreater(len(evidence), 0)
        for ev in evidence:
            self.assertTrue(ev.id)
            self.assertTrue(ev.observation_id)
        manager.stop()


# ---------------------------------------------------------------------------
# MCP tool tests
# ---------------------------------------------------------------------------

class Phase15MCPToolTests(unittest.TestCase):
    def test_evidence_tools_in_list(self):
        from services.mcp_tool_service import MCPToolService
        kernel = DummyKernel()
        tool_svc = MCPToolService(kernel)
        tool_svc.evidence_ingestion = None
        tools = tool_svc.list_tools()
        tool_names = [t["name"] for t in tools]
        self.assertIn("get_evidence_stats", tool_names)
        self.assertIn("get_connector_evidence", tool_names)

    def test_get_evidence_stats_returns_error_when_unavailable(self):
        from services.mcp_tool_service import MCPToolService
        kernel = DummyKernel()
        tool_svc = MCPToolService(kernel)
        tool_svc.evidence_ingestion = None
        result = tool_svc.call_tool("get_evidence_stats", {})
        self.assertIn("error", result)

    def test_get_connector_evidence_returns_error_when_unavailable(self):
        from services.mcp_tool_service import MCPToolService
        kernel = DummyKernel()
        tool_svc = MCPToolService(kernel)
        tool_svc.connector = None
        result = tool_svc.call_tool("get_connector_evidence", {"connector_id": "mock"})
        self.assertIn("error", result)

    def test_existing_tools_preserved(self):
        from services.mcp_tool_service import MCPToolService
        kernel = DummyKernel()
        tool_svc = MCPToolService(kernel)
        tools = tool_svc.list_tools()
        tool_names = [t["name"] for t in tools]
        for name in ["search_memory", "build_context", "get_document",
                      "get_recent_events", "reindex_memory", "cross_reference",
                      "explain_change", "get_causal_chain", "compare_snapshots",
                      "list_decisions", "get_decision", "search_semantic",
                      "get_similar", "get_awareness_signals",
                      "list_connectors", "get_connector_status",
                      "get_connector_health_all"]:
            self.assertIn(name, tool_names)


if __name__ == "__main__":
    unittest.main()
