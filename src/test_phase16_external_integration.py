"""Phase 16 — External Project Integration Layer (v2.4.0).

Tests: ObservationDiscoveryEngine, authentication, webhook framework,
sync engine, metrics, REST connector base, GitHub connector, scheduler
service, new MCP tools, backward compatibility.
"""

import json
import os
import tempfile
import time
import unittest

from connectors.observation_discovery import (
    ObservationDiscoveryEngine, ObservationSurface, SurfaceQuality,
    EvidenceQuality, LatencyClass, Completeness, Reliability,
)
from connectors.auth import PATAuth, OAuthAuth, APIKeyAuth, BearerTokenAuth, AuthConfig
from connectors.webhooks import WebhookHandler, SignatureVerifier, WebhookRegistry, ReplayGuard
from connectors.sync import SyncEngine, SyncStore, SyncCheckpoint
from connectors.metrics import MetricsCollector
from connectors.models import (
    Source, RawPayload, Observation, Evidence, NormalizedPayload, TraceInformation,
)
from connectors.manifest import ConnectorManifest, ManifestParser
from connectors.validator import ManifestValidator
from connectors.sdk import ConnectorSDK
from connectors.plugins.github_connector import GitHubConnector
from connectors.plugins.mock_connector import MockConnector
from connectors.plugins.filesystem_connector import FilesystemConnector
from connectors.plugins.git_connector import GitConnector
from services.connector_scheduler_service import ConnectorSchedulerService


class DummyKernel:
    def __init__(self):
        self.services = {}
        self.config = {}

    def get_service(self, name):
        return self.services.get(name)

    def register_service(self, svc):
        self.services[svc.name] = svc

    def get_config(self):
        return self.config

    def set_config(self, config):
        self.config = config


class DummyEventBus:
    def __init__(self):
        self.events = []

    def subscribe(self, event, cb):
        pass

    def publish(self, event, data):
        self.events.append((event, data))


class Phase16ObservationDiscoveryTests(unittest.TestCase):
    def test_discover_from_manifest(self):
        class FakeConnector:
            observation_surfaces = [ObservationSurface.OFFICIAL_API, ObservationSurface.WEBHOOK]
            manifest = None
        engine = ObservationDiscoveryEngine()
        surfaces = engine.discover_surfaces(FakeConnector())
        self.assertIn(ObservationSurface.OFFICIAL_API, surfaces)
        self.assertIn(ObservationSurface.WEBHOOK, surfaces)
        self.assertEqual(len(surfaces), 2)

    def test_discover_from_manifest_object(self):
        m = ConnectorManifest(connector_id="test", name="Test", version="1.0",
                               observation_surfaces=["official_api", "git_repository"])
        class FakeConnector:
            observation_surfaces = None
            manifest = m
        engine = ObservationDiscoveryEngine()
        surfaces = engine.discover_surfaces(FakeConnector())
        self.assertEqual(len(surfaces), 2)

    def test_rank_surfaces_by_score(self):
        engine = ObservationDiscoveryEngine()
        surfaces = [ObservationSurface.OFFICIAL_API, ObservationSurface.WEBHOOK]
        qualities = {
            ObservationSurface.WEBHOOK: SurfaceQuality(
                surface=ObservationSurface.WEBHOOK,
                quality=EvidenceQuality.HIGH,
                latency=LatencyClass.REALTIME,
                completeness=Completeness.PARTIAL,
                reliability=Reliability.MEDIUM,
                supports_incremental_sync=False,
                authentication_required="token",
            ),
            ObservationSurface.OFFICIAL_API: SurfaceQuality(
                surface=ObservationSurface.OFFICIAL_API,
                quality=EvidenceQuality.HIGH,
                latency=LatencyClass.NEAR_REALTIME,
                completeness=Completeness.FULL,
                reliability=Reliability.HIGH,
                supports_incremental_sync=True,
                authentication_required="token",
            ),
        }
        ranked = engine.rank_surfaces(surfaces, qualities)
        first_surface, first_quality = ranked[0]
        self.assertEqual(first_surface, ObservationSurface.OFFICIAL_API)
        self.assertGreater(first_quality.score, ranked[1][1].score)

    def test_select_pipeline_includes_both_api_and_webhook(self):
        engine = ObservationDiscoveryEngine()
        surfaces = [ObservationSurface.OFFICIAL_API, ObservationSurface.WEBHOOK,
                     ObservationSurface.LOCAL_WORKSPACE]
        qualities = {
            ObservationSurface.OFFICIAL_API: SurfaceQuality(
                ObservationSurface.OFFICIAL_API, EvidenceQuality.HIGH,
                LatencyClass.NEAR_REALTIME, Completeness.FULL, Reliability.HIGH,
                supports_incremental_sync=True, authentication_required="token"),
            ObservationSurface.WEBHOOK: SurfaceQuality(
                ObservationSurface.WEBHOOK, EvidenceQuality.HIGH,
                LatencyClass.REALTIME, Completeness.PARTIAL, Reliability.MEDIUM,
                supports_incremental_sync=False, authentication_required="token"),
            ObservationSurface.LOCAL_WORKSPACE: SurfaceQuality(
                ObservationSurface.LOCAL_WORKSPACE, EvidenceQuality.MEDIUM,
                LatencyClass.BATCH, Completeness.PARTIAL, Reliability.HIGH,
                supports_incremental_sync=True, authentication_required="none"),
        }
        ranked = engine.rank_surfaces(surfaces, qualities)
        pipeline = engine.select_pipeline(ranked, max_surfaces=3)
        self.assertIn(ObservationSurface.OFFICIAL_API, pipeline)
        self.assertIn(ObservationSurface.WEBHOOK, pipeline)

    def test_surface_quality_score_ranges(self):
        high = SurfaceQuality(ObservationSurface.OFFICIAL_API, EvidenceQuality.HIGH,
                               LatencyClass.REALTIME, Completeness.FULL, Reliability.HIGH,
                               supports_incremental_sync=True, authentication_required="none")
        low = SurfaceQuality(ObservationSurface.LOGS, EvidenceQuality.LOW,
                              LatencyClass.BATCH, Completeness.MINIMAL, Reliability.LOW,
                              supports_incremental_sync=False, authentication_required="none")
        self.assertGreater(high.score, low.score)


class Phase16AuthTests(unittest.TestCase):
    def test_pat_auth(self):
        auth = PATAuth(token="ghp_test123")
        self.assertTrue(auth.authenticate())
        headers = auth.get_headers()
        self.assertEqual(headers["Authorization"], "Bearer ghp_test123")
        sanitized = auth.sanitize()
        self.assertTrue(sanitized["token_present"])
        self.assertNotIn("ghp_test123", str(sanitized))

    def test_pat_empty_token_fails(self):
        auth = PATAuth(token="")
        self.assertFalse(auth.authenticate())

    def test_oauth_auth(self):
        auth = OAuthAuth(access_token="access_123", refresh_token="refresh_456")
        self.assertTrue(auth.authenticate())
        headers = auth.get_headers()
        self.assertEqual(headers["Authorization"], "Bearer access_123")
        sanitized = auth.sanitize()
        self.assertTrue(sanitized["has_refresh"])
        self.assertNotIn("access_123", str(sanitized))

    def test_api_key_auth(self):
        auth = APIKeyAuth(api_key="key_abc123", header_name="X-Custom-Key")
        self.assertTrue(auth.authenticate())
        headers = auth.get_headers()
        self.assertEqual(headers["X-Custom-Key"], "key_abc123")

    def test_bearer_token_auth(self):
        auth = BearerTokenAuth(token="bearer_token_789")
        self.assertTrue(auth.authenticate())
        self.assertIn("Bearer", auth.get_headers().get("Authorization", ""))

    def test_auth_validate(self):
        auth = BearerTokenAuth(token="tok", config=AuthConfig(provider="bearer"))
        self.assertEqual(auth.validate(), [])
        auth.config.provider = ""
        self.assertGreater(len(auth.validate()), 0)


class Phase16WebhookTests(unittest.TestCase):
    def test_receive_and_queue(self):
        handler = WebhookHandler()
        handler.get_registry().register("github", secret="test_secret")
        body = json.dumps({"action": "opened", "number": 1}).encode()
        event = handler.receive("github", body, {
            "X-GitHub-Event": "pull_request",
            "X-Webhook-Id": "evt_001",
        })
        self.assertEqual(event.event_type, "pull_request")
        self.assertEqual(event.connector_id, "github")
        self.assertEqual(handler.get_queue().size(), 1)

    def test_signature_verification_hmac(self):
        verifier = SignatureVerifier()
        body = b'{"test": "data"}'
        sig = __import__("hmac").new(b"secret", body, "sha256").hexdigest()
        self.assertTrue(verifier.verify_hmac(body, sig, "secret"))
        self.assertFalse(verifier.verify_hmac(body, "bad_sig", "secret"))

    def test_replay_guard_rejects_duplicate(self):
        guard = ReplayGuard()
        self.assertTrue(guard.is_new("evt_001", time.time()))
        self.assertFalse(guard.is_new("evt_001", time.time()))

    def test_webhook_registry(self):
        reg = WebhookRegistry()
        reg.register("test", secret="s", webhook_url="http://example.com/hook", events=["push"])
        info = reg.get("test")
        self.assertIsNotNone(info)
        self.assertEqual(info["webhook_url"], "http://example.com/hook")
        reg.unregister("test")
        self.assertIsNone(reg.get("test"))


class Phase16SyncTests(unittest.TestCase):
    def test_initial_sync(self):
        engine = SyncEngine()
        collected = []
        def fetch(cursor):
            if len(collected) >= 5:
                return None
            items = [{"id": f"item_{len(collected)}"}]
            collected.extend(items)
            return (items, f"cursor_{len(collected)}", len(collected) < 5)
        stats, items = engine.initial_sync("test", "api", fetch)
        self.assertEqual(stats.items_synced, 5)

    def test_checkpoint_save_and_load(self):
        store = SyncStore()
        cp = SyncCheckpoint(connector_id="test", surface="api", cursor="abc123")
        store.save_checkpoint(cp)
        loaded = store.load_checkpoint("test", "api")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.cursor, "abc123")

    def test_delta_sync_uses_checkpoint(self):
        store = SyncStore()
        cp = SyncCheckpoint(connector_id="test", surface="api", cursor="page_2",
                             completed=True, item_count=10)
        store.save_checkpoint(cp)
        engine = SyncEngine(store=store)
        fetch_called = [False]
        def fetch(cursor):
            fetch_called[0] = True
            self.assertEqual(cursor, "page_2")
            return ([{"id": "new"}], "page_3", False)
        engine.delta_sync("test", "api", fetch)
        self.assertTrue(fetch_called[0])

    def test_resume_returns_none_when_completed(self):
        store = SyncStore()
        store.save_checkpoint(SyncCheckpoint("test", "api", completed=True))
        engine = SyncEngine(store=store)
        result = engine.resume("test", "api", lambda c: None)
        self.assertIsNone(result)

    def test_conflict_detection(self):
        engine = SyncEngine()
        self.assertTrue(engine.detect_conflict("abc", "def"))
        self.assertFalse(engine.detect_conflict("abc", "abc"))


class Phase16MetricsTests(unittest.TestCase):
    def test_register_and_record(self):
        mc = MetricsCollector()
        mc.register_connector("test")
        mc.record_sync("test", 100.0, 50)
        mc.record_api_request("test")
        mc.record_failure("test", "timeout")
        metrics = mc.get_metrics("test")
        self.assertIsNotNone(metrics)
        self.assertEqual(metrics.sync_count, 1)
        self.assertEqual(metrics.api_requests, 1)
        self.assertEqual(metrics.failures, 1)

    def test_get_all_metrics(self):
        mc = MetricsCollector()
        mc.register_connector("a")
        mc.register_connector("b")
        mc.record_sync("a", 50.0, 10)
        all_m = mc.get_all_metrics()
        self.assertIn("a", all_m)
        self.assertIn("b", all_m)

    def test_health_details_includes_metrics(self):
        mc = MetricsCollector()
        mc.register_connector("test")
        details = mc.get_health_details("test", {"state": "running"})
        self.assertEqual(details["health"]["state"], "running")
        self.assertEqual(details["connector_id"], "test")


class Phase16ConnectorSurfaceTests(unittest.TestCase):
    def test_filesystem_implements_surfaces(self):
        fc = FilesystemConnector({"paths": [tempfile.gettempdir()]})
        surfaces = fc.discover_observation_surfaces()
        self.assertIn(ObservationSurface.LOCAL_WORKSPACE, surfaces)
        ranked = fc.rank_observation_surfaces()
        self.assertGreater(len(ranked), 0)
        pipeline = fc.select_observation_pipeline()
        self.assertGreater(len(pipeline), 0)

    def test_git_implements_surfaces(self):
        gc = GitConnector({"repo_path": os.getcwd()})
        surfaces = gc.discover_observation_surfaces()
        self.assertIn(ObservationSurface.GIT_REPOSITORY, surfaces)
        ranked = gc.rank_observation_surfaces()
        self.assertGreater(len(ranked), 0)
        pipeline = gc.select_observation_pipeline()
        self.assertGreater(len(pipeline), 0)

    def test_mock_implements_surfaces(self):
        mc = MockConnector()
        surfaces = mc.discover_observation_surfaces()
        self.assertIn(ObservationSurface.OTHER, surfaces)
        ranked = mc.rank_observation_surfaces()
        self.assertGreater(len(ranked), 0)
        pipeline = mc.select_observation_pipeline()
        self.assertGreater(len(pipeline), 0)

    def test_github_implements_surfaces(self):
        gc = GitHubConnector({"owner": "test", "repo": "test", "token": ""})
        surfaces = gc.discover_observation_surfaces()
        self.assertIn(ObservationSurface.OFFICIAL_API, surfaces)
        self.assertIn(ObservationSurface.GIT_REPOSITORY, surfaces)
        self.assertIn(ObservationSurface.WEBHOOK, surfaces)
        ranked = gc.rank_observation_surfaces()
        self.assertGreater(len(ranked), 0)
        pipeline = gc.select_observation_pipeline()
        self.assertGreater(len(pipeline), 0)
        active = gc.get_active_surfaces()
        self.assertGreater(len(active), 0)

    def test_github_connector_status_shape(self):
        gc = GitHubConnector({"owner": "test", "repo": "test", "token": ""})
        status = gc.status()
        self.assertEqual(status["id"], "github")
        self.assertIn("capabilities", status)
        self.assertIn("permissions", status)
        self.assertIn("state", status)


class Phase16ManifestExtensionTests(unittest.TestCase):
    def test_manifest_observation_fields(self):
        manifest_json = json.dumps({
            "connector_id": "github",
            "name": "GitHub Connector",
            "version": "1.0.0",
            "observation_surfaces": ["official_api", "git_repository"],
            "preferred_surface": "auto",
            "supports_multi_surface": True,
            "supports_incremental_sync": True,
            "supports_realtime": False,
        })
        manifest = ManifestParser.parse_string(manifest_json, format_="json")
        self.assertIn("official_api", manifest.observation_surfaces)
        self.assertEqual(manifest.preferred_surface, "auto")
        self.assertTrue(manifest.supports_multi_surface)
        self.assertTrue(manifest.supports_incremental_sync)
        self.assertFalse(manifest.supports_realtime)

    def test_manifest_validator_validates_surfaces(self):
        manifest = ConnectorManifest(
            connector_id="test", name="Test", version="1.0",
            observation_surfaces=["official_api", "invalid_surface"],
        )
        errors = ManifestValidator.validate(manifest)
        surface_errors = [e for e in errors if "observation surface" in e]
        self.assertEqual(len(surface_errors), 1)

    def test_sdk_run_observation_discovery(self):
        mc = MockConnector()
        result = ConnectorSDK.run_observation_discovery(mc)
        self.assertEqual(result["connector_id"], "mock")
        self.assertGreater(len(result["surfaces"]), 0)
        self.assertGreater(len(result["pipeline"]), 0)


class Phase16SchedulerTests(unittest.TestCase):
    def test_register_and_schedule(self):
        kernel = DummyKernel()
        scheduler = ConnectorSchedulerService(kernel)
        called = [False]
        def sync_fn():
            called[0] = True
            return {"items": 5}
        scheduler.register("test", 1.0, sync_fn, enabled=True)
        schedule = scheduler.get_schedule()
        self.assertEqual(len(schedule), 1)
        self.assertEqual(schedule[0]["connector_id"], "test")

    def test_trigger_sync(self):
        kernel = DummyKernel()
        scheduler = ConnectorSchedulerService(kernel)
        def sync_fn():
            return {"items": 5}
        scheduler.register("test", 1.0, sync_fn)
        result = scheduler.trigger_sync("test")
        self.assertIsNotNone(result)
        self.assertEqual(result["connector_id"], "test")
        self.assertEqual(result["status"], "completed")

    def test_trigger_sync_handles_failure(self):
        kernel = DummyKernel()
        scheduler = ConnectorSchedulerService(kernel)
        def sync_fn():
            raise RuntimeError("sync failed")
        scheduler.register("test", 1.0, sync_fn)
        result = scheduler.trigger_sync("test")
        self.assertEqual(result["status"], "failed")

    def test_should_run_backoff(self):
        from services.connector_scheduler_service import ScheduleEntry
        entry = ScheduleEntry("test", 10.0, lambda: None)
        entry.last_run = time.time() - 5
        self.assertFalse(entry.should_run())
        entry.consecutive_failures = 2
        self.assertFalse(entry.should_run())
        entry.last_run = time.time() - 45
        self.assertTrue(entry.should_run())


class Phase16McpToolTests(unittest.TestCase):
    def setUp(self):
        self.kernel = DummyKernel()
        self.kernel.services["ConnectorService"] = None
        self.kernel.services["EvidenceIngestionService"] = None
        self.kernel.services["ConnectorSchedulerService"] = None
        from services.mcp_tool_service import MCPToolService
        self.tool_svc = MCPToolService(self.kernel)
        self.tool_svc.connector = None
        self.tool_svc.scheduler = None

    def test_new_tools_in_list(self):
        tools = self.tool_svc.list_tools()
        names = [t["name"] for t in tools]
        for tool in ["github_connector_status", "connector_sync",
                      "connector_metrics", "connector_last_sync",
                      "connector_health_details"]:
            self.assertIn(tool, names)

    def test_existing_tools_preserved(self):
        tools = self.tool_svc.list_tools()
        names = [t["name"] for t in tools]
        for tool in ["search_memory", "build_context", "get_document",
                      "get_recent_events", "reindex_memory", "cross_reference",
                      "explain_change", "get_causal_chain", "compare_snapshots",
                      "list_decisions", "get_decision", "search_semantic",
                      "get_similar", "get_awareness_signals", "list_connectors",
                      "get_connector_status", "get_connector_health_all",
                      "get_evidence_stats", "get_connector_evidence"]:
            self.assertIn(tool, names)

    def test_new_tools_return_error_when_unavailable(self):
        for tool in ["github_connector_status", "connector_sync",
                      "connector_metrics", "connector_last_sync",
                      "connector_health_details"]:
            result = self.tool_svc.call_tool(tool, {})
            self.assertIn("error", result, f"{tool} should return error when unavailable")

    def test_all_tools_24_total(self):
        tools = self.tool_svc.list_tools()
        self.assertEqual(len(tools), 24)


class Phase16SDKRunPipelineFixTests(unittest.TestCase):
    def test_run_pipeline_no_hasattr(self):
        mc = MockConnector()
        mc.connect()
        evidence_list = ConnectorSDK.run_pipeline(mc)
        self.assertGreater(len(evidence_list), 0)


class Phase15OneFixVerificationTests(unittest.TestCase):
    def test_evidence_bus_shim_connected(self):
        from services.evidence_ingestion_service import EvidenceBusShim
        from connectors.connector_manager import ConnectorManager
        bus = DummyEventBus()
        manager = ConnectorManager(auto_discover=False, event_bus=bus)
        manager.start()
        from connectors.plugins.mock_connector import MockConnector
        mc = MockConnector()
        mc.connect()
        manager._registry.register(mc)
        evidence_bus = manager.get_evidence_bus()
        self.assertIsNotNone(evidence_bus)
        received = []
        evidence_bus.subscribe(lambda cid, ev: received.append((cid, len(ev))))
        evidence = manager.collect_evidence("mock")
        self.assertGreater(len(received), 0)
        manager.stop()

    def test_get_connector_evidence_persists(self):
        from services.mcp_tool_service import MCPToolService
        from core.event_bus import EventBus
        class MiniStore:
            name = "MiniStore"
            def __init__(self):
                self.events = []
            def record_event(self, event_type, path, payload):
                self.events.append((event_type, path, payload))
            def get_document(self, path):
                return None
        class MiniConnector:
            def __init__(self):
                self._manager = None
            def get_manager(self):
                return self._manager
            def set_manager(self, m):
                self._manager = m
        class MiniIngestion:
            def __init__(self):
                self.calls = []
            def ingest(self, cid, ev):
                self.calls.append((cid, len(ev)))
                return {"ingested": len(ev)}
            def get_stats(self):
                return {"ingested_count": len(self.calls)}
        kernel = DummyKernel()
        kernel.register_service(MiniStore())
        bus = EventBus()
        from connectors.connector_manager import ConnectorManager
        manager = ConnectorManager(auto_discover=False, event_bus=bus)
        manager.start()
        mc = MockConnector()
        mc.connect()
        manager._registry.register(mc)
        conn_svc = MiniConnector()
        conn_svc.set_manager(manager)
        kernel.services["ConnectorService"] = conn_svc
        kernel.services["EvidenceIngestionService"] = MiniIngestion()
        kernel.services["RetrievalService"] = None
        kernel.services["ContextBuilderService"] = None
        kernel.services["KnowledgeIndexerService"] = None
        kernel.services["KnowledgeStoreService"] = kernel.get_service("MiniStore")
        kernel.services["CrossReferenceService"] = None
        kernel.services["CausalGraphService"] = None
        kernel.services["ArchitectureEvolutionService"] = None
        kernel.services["DecisionTrackingService"] = None
        kernel.services["CognitiveLayerService"] = None
        kernel.services["VectorSearchService"] = None
        kernel.services["SemanticAwarenessService"] = None
        kernel.services["ConnectorSchedulerService"] = None
        tool_svc = MCPToolService(kernel)
        tool_svc.start()
        result = tool_svc.call_tool("get_connector_evidence", {"connector_id": "mock"})
        self.assertIn("ingested", result)
        self.assertIn("evidence_count", result)
        manager.stop()


if __name__ == "__main__":
    unittest.main()
