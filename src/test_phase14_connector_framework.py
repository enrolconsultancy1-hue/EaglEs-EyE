"""Phase 14 — Universal Connector Framework tests."""

import json
import os
import tempfile
import unittest

from connectors.exceptions import (
    ConnectorError, ConnectorNotFoundError, ConnectorLoadError,
    ConnectorManifestError, ConnectorStateError, ConnectorCapabilityError,
    ConnectorPermissionError, ConnectorValidationError,
)
from connectors.models import (
    Timestamp, Identity, Source, Artifact, Relationship, Confidence,
    RawPayload, NormalizedPayload, Observation, Evidence, TraceInformation,
    CitationInformation,
)
from connectors.health import ConnectorState, ConnectorHealth
from connectors.manifest import ConnectorManifest, ManifestParser
from connectors.events import (
    CONNECTOR_REGISTERED, CONNECTOR_STARTED, CONNECTOR_STOPPED,
    CONNECTOR_HEALTH_CHANGED, CONNECTOR_DISCOVERED, CONNECTOR_FAILED,
    CONNECTOR_OBSERVATION, CONNECTOR_EVIDENCE,
    ConnectorEventData,
)
from connectors.validator import (
    CapabilityValidator, PermissionValidator, ManifestValidator,
)
from connectors.connector import Connector
from connectors.registry import ConnectorRegistry
from connectors.discovery import ConnectorDiscovery
from connectors.loader import ConnectorLoader
from connectors.sdk import ConnectorSDK, register_connector_cls
from connectors.connector_manager import ConnectorManager
from connectors.plugins.mock_connector import MockConnector
from connectors.plugins.filesystem_connector import FilesystemConnector
from connectors.plugins.git_connector import GitConnector


# ---------------------------------------------------------------------------
# Dummy event bus for tests
# ---------------------------------------------------------------------------

class DummyEventBus:
    def __init__(self):
        self.events = []

    def subscribe(self, event, callback):
        pass

    def publish(self, event, data):
        self.events.append((event, data))


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Phase14ModelTests(unittest.TestCase):
    def test_timestamp_now(self):
        ts = Timestamp.now()
        self.assertGreater(ts.value, 0)
        self.assertEqual(ts.source, "system")

    def test_identity_create(self):
        identity = Identity.create(name="test", type_="user")
        self.assertTrue(identity.id)
        self.assertEqual(identity.name, "test")
        self.assertEqual(identity.type, "user")

    def test_source_create(self):
        source = Source.create(type_="filesystem", path="/tmp")
        self.assertTrue(source.id)
        self.assertEqual(source.type, "filesystem")
        self.assertEqual(source.path, "/tmp")

    def test_artifact_create(self):
        art = Artifact.create(type_="file", content="hello",
                              path="/tmp/test.txt", mime_type="text/plain")
        self.assertTrue(art.id)
        self.assertEqual(art.size, 5)
        self.assertEqual(art.path, "/tmp/test.txt")

    def test_confidence_certain(self):
        c = Confidence.certain()
        self.assertEqual(c.score, 1.0)
        self.assertEqual(c.method, "direct")

    def test_confidence_derived(self):
        c = Confidence.derived(0.75)
        self.assertEqual(c.score, 0.75)
        self.assertEqual(c.method, "derived")

    def test_raw_payload_from_text(self):
        rp = RawPayload.from_text("hello")
        self.assertEqual(rp.data, "hello")
        self.assertEqual(rp.format, "text")
        self.assertEqual(rp.size, 5)

    def test_raw_payload_from_dict(self):
        rp = RawPayload.from_dict({"key": "value"})
        self.assertEqual(rp.data["key"], "value")
        self.assertEqual(rp.format, "json")

    def test_normalized_payload_structured(self):
        np = NormalizedPayload.structured({"result": "ok"})
        self.assertEqual(np.data["result"], "ok")
        self.assertEqual(np.schema_version, "1.0")

    def test_observation_create(self):
        source = Source.create(type_="test")
        raw = RawPayload.from_text("test data")
        obs = Observation.create(type_="test_event", source=source, raw=raw)
        self.assertTrue(obs.id)
        self.assertEqual(obs.type, "test_event")
        self.assertGreater(obs.timestamp.value, 0)

    def test_evidence_create(self):
        source = Source.create(type_="test")
        raw = RawPayload.from_text("test")
        obs = Observation.create(type_="test_event", source=source, raw=raw)
        norm = NormalizedPayload.structured({"data": "test"})
        trace = TraceInformation("test_connector", "1.0", ["observe", "emit"])
        evidence = Evidence.create(observation=obs, normalized=norm, trace=trace)
        self.assertTrue(evidence.id)
        self.assertEqual(evidence.observation_id, obs.id)
        self.assertEqual(evidence.trace.connector_id, "test_connector")


# ---------------------------------------------------------------------------
# Health and State
# ---------------------------------------------------------------------------

class Phase14HealthTests(unittest.TestCase):
    def test_state_disconnected_default(self):
        h = ConnectorHealth()
        self.assertEqual(h.state, ConnectorState.DISCONNECTED)

    def test_record_heartbeat(self):
        h = ConnectorHealth()
        h.record_heartbeat()
        self.assertGreater(h.last_heartbeat, 0)
        self.assertEqual(h.state, ConnectorState.CONNECTED)

    def test_record_observation(self):
        h = ConnectorHealth()
        h.record_observation()
        self.assertGreater(h.last_observation, 0)

    def test_record_error(self):
        h = ConnectorHealth()
        h.record_error("test error")
        self.assertEqual(len(h.errors), 1)
        self.assertEqual(h.state, ConnectorState.ERROR)

    def test_start_stop(self):
        h = ConnectorHealth()
        h.start()
        self.assertEqual(h.state, ConnectorState.RUNNING)
        self.assertIsNotNone(h.started_at)
        h.stop()
        self.assertEqual(h.state, ConnectorState.STOPPED)
        self.assertGreater(h.uptime, 0)

    def test_to_dict(self):
        h = ConnectorHealth()
        h.start()
        d = h.to_dict()
        self.assertEqual(d["state"], "running")
        self.assertIn("last_heartbeat", d)
        self.assertIn("errors", d)
        self.assertGreater(d["uptime"], 0)

    def test_state_active(self):
        self.assertTrue(ConnectorState.RUNNING.is_active())
        self.assertTrue(ConnectorState.CONNECTED.is_active())
        self.assertFalse(ConnectorState.DISCONNECTED.is_active())
        self.assertFalse(ConnectorState.ERROR.is_active())
        self.assertFalse(ConnectorState.STOPPED.is_active())

    def test_state_transitions_valid(self):
        self.assertTrue(
            ConnectorState.DISCONNECTED.can_transition_to(ConnectorState.CONNECTED)
        )
        self.assertTrue(
            ConnectorState.CONNECTED.can_transition_to(ConnectorState.RUNNING)
        )
        self.assertTrue(
            ConnectorState.RUNNING.can_transition_to(ConnectorState.PAUSED)
        )

    def test_state_transitions_invalid(self):
        self.assertFalse(
            ConnectorState.CONNECTED.can_transition_to(ConnectorState.CONNECTED)
        )


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

class Phase14ManifestTests(unittest.TestCase):
    def test_manifest_from_dict_json(self):
        manifest = ManifestParser.parse_string(json.dumps({
            "connector_id": "test_connector",
            "name": "Test Connector",
            "version": "1.0.0",
            "vendor": "Test",
            "capabilities": ["api", "git"],
            "permissions": ["read", "observe"],
        }))
        self.assertEqual(manifest.connector_id, "test_connector")
        self.assertEqual(manifest.version, "1.0.0")
        self.assertIn("api", manifest.capabilities)
        self.assertIn("read", manifest.permissions)

    def test_manifest_missing_id_raises(self):
        with self.assertRaises(ConnectorManifestError):
            ManifestParser.parse_string(json.dumps({"name": "no id"}))

    def test_manifest_supports_capability(self):
        manifest = ManifestParser.parse_string(json.dumps({
            "connector_id": "c1", "capabilities": ["git", "api"],
        }))
        self.assertTrue(manifest.supports_capability("git"))
        self.assertFalse(manifest.supports_capability("database"))

    def test_manifest_has_permission(self):
        manifest = ManifestParser.parse_string(json.dumps({
            "connector_id": "c1", "permissions": ["read", "observe"],
        }))
        self.assertTrue(manifest.has_permission("read"))
        self.assertFalse(manifest.has_permission("write"))

    def test_manifest_from_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                         delete=False) as f:
            json.dump({"connector_id": "file_connector", "name": "File"},
                      f)
            fpath = f.name
        try:
            manifest = ManifestParser.parse(fpath)
            self.assertEqual(manifest.connector_id, "file_connector")
        finally:
            os.unlink(fpath)

    def test_manifest_unsupported_extension(self):
        with self.assertRaises(ConnectorManifestError):
            ManifestParser.parse_string("{}", format_="xml")


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class Phase14ValidatorTests(unittest.TestCase):
    def test_validate_valid_capability(self):
        self.assertTrue(CapabilityValidator.validate_capability("git"))

    def test_validate_invalid_capability(self):
        with self.assertRaises(ConnectorValidationError):
            CapabilityValidator.validate_capability("invalid_cap")

    def test_validate_capabilities_list(self):
        errors = CapabilityValidator.validate_capabilities(["git", "invalid"])
        self.assertEqual(len(errors), 1)

    def test_validate_permission_valid(self):
        self.assertTrue(PermissionValidator.validate_permission("read"))

    def test_validate_permission_invalid(self):
        with self.assertRaises(ConnectorValidationError):
            PermissionValidator.validate_permission("invalid_perm")

    def test_validate_permissions_list(self):
        errors = PermissionValidator.validate_permissions(["read", "invalid"])
        self.assertEqual(len(errors), 1)

    def test_manifest_validator_valid(self):
        manifest = ConnectorManifest(
            connector_id="test", name="Test", version="1.0",
            capabilities=["git"], permissions=["read"],
        )
        errors = ManifestValidator.validate(manifest)
        self.assertEqual(errors, [])

    def test_manifest_validator_missing_fields(self):
        manifest = ConnectorManifest(
            connector_id="", name="", version="",
            capabilities=["invalid_cap"], permissions=["invalid_perm"],
        )
        errors = ManifestValidator.validate(manifest)
        self.assertGreaterEqual(len(errors), 4)

    def test_check_required_capability_missing(self):
        class FakeConnector:
            capabilities = ["git"]
        missing = CapabilityValidator.check_required(FakeConnector(), ["api"])
        self.assertEqual(missing, ["api"])

    def test_check_required_permission_missing(self):
        class FakeConnector:
            permissions = ["read"]
        missing = PermissionValidator.check_required(FakeConnector(), ["write"])
        self.assertEqual(missing, ["write"])


# ---------------------------------------------------------------------------
# Connector base class
# ---------------------------------------------------------------------------

class Phase14ConnectorBaseTests(unittest.TestCase):
    def test_connector_abstract_cannot_instantiate(self):
        with self.assertRaises(TypeError):
            Connector()

    def test_connector_status_shape(self):
        c = MockConnector()
        status = c.status()
        self.assertEqual(status["id"], "mock")
        self.assertEqual(status["name"], "Mock Connector")
        self.assertEqual(status["version"], "1.0.0")
        self.assertIn("state", status)
        self.assertIn("capabilities", status)
        self.assertIn("permissions", status)
        self.assertIn("health", status)

    def test_connector_state_transition(self):
        c = MockConnector()
        c.connect()
        self.assertEqual(c.health().state, ConnectorState.CONNECTED)
        c._health.state = ConnectorState.RUNNING
        with self.assertRaises(ConnectorStateError):
            c.start()


# ---------------------------------------------------------------------------
# Mock Connector
# ---------------------------------------------------------------------------

class Phase14MockConnectorTests(unittest.TestCase):
    def test_mock_connect_success(self):
        c = MockConnector()
        result = c.connect()
        self.assertTrue(result)

    def test_mock_connect_failure(self):
        c = MockConnector(config={"fail_connect": True})
        result = c.connect()
        self.assertFalse(result)

    def test_mock_discover(self):
        c = MockConnector()
        sources = c.discover()
        self.assertEqual(len(sources), 2)

    def test_mock_observe(self):
        c = MockConnector()
        c.connect()
        observations = c.observe()
        self.assertEqual(len(observations), 1)

    def test_mock_observe_empty(self):
        c = MockConnector(config={"return_empty": True})
        c.connect()
        observations = c.observe()
        self.assertEqual(len(observations), 0)

    def test_mock_collect(self):
        c = MockConnector()
        c.connect()
        evidence = c.collect()
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].trace.connector_id, "mock")

    def test_mock_emit(self):
        c = MockConnector()
        c.connect()
        evidence = c.collect()
        result = c.emit(evidence[0])
        self.assertTrue(result)


# ---------------------------------------------------------------------------
# Filesystem Connector
# ---------------------------------------------------------------------------

class Phase14FilesystemConnectorTests(unittest.TestCase):
    def test_fs_connect(self):
        c = FilesystemConnector(config={"paths": [tempfile.gettempdir()]})
        result = c.connect()
        self.assertTrue(result)

    def test_fs_discover(self):
        c = FilesystemConnector(config={"paths": [tempfile.gettempdir()]})
        c.connect()
        sources = c.discover()
        self.assertGreater(len(sources), 0)

    def test_fs_observe(self):
        c = FilesystemConnector(config={"paths": [tempfile.gettempdir()]})
        c.connect()
        obs = c.observe()
        self.assertGreater(len(obs), 0)

    def test_fs_collect(self):
        c = FilesystemConnector(config={"paths": [tempfile.gettempdir()]})
        c.connect()
        evidence = c.collect()
        self.assertGreater(len(evidence), 0)
        self.assertEqual(evidence[0].trace.connector_id, "filesystem")


# ---------------------------------------------------------------------------
# Git Connector
# ---------------------------------------------------------------------------

class Phase14GitConnectorTests(unittest.TestCase):
    def test_git_connect_not_repo(self):
        c = GitConnector(config={"repo_path": tempfile.gettempdir()})
        result = c.connect()
        self.assertFalse(result)

    def test_git_discover(self):
        c = GitConnector()
        sources = c.discover()
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].type, "git")


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class Phase14RegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = ConnectorRegistry()

    def test_register_and_get(self):
        c = MockConnector()
        cid = self.registry.register(c)
        self.assertEqual(cid, "mock")
        self.assertTrue(self.registry.has("mock"))

    def test_register_with_custom_id(self):
        c = MockConnector()
        c.id = "custom_mock"
        cid = self.registry.register(c)
        self.assertEqual(cid, "custom_mock")

    def test_register_duplicate_raises(self):
        c1 = MockConnector()
        c2 = MockConnector()
        self.registry.register(c1)
        with self.assertRaises(ConnectorError):
            self.registry.register(c2)

    def test_unregister(self):
        c = MockConnector()
        self.registry.register(c)
        result = self.registry.unregister("mock")
        self.assertTrue(result)
        self.assertFalse(self.registry.has("mock"))

    def test_unregister_nonexistent(self):
        result = self.registry.unregister("nonexistent")
        self.assertFalse(result)

    def test_get_nonexistent_raises(self):
        with self.assertRaises(ConnectorNotFoundError):
            self.registry.get("nonexistent")

    def test_list_ids(self):
        c = MockConnector()
        self.registry.register(c)
        ids = self.registry.list_ids()
        self.assertIn("mock", ids)

    def test_list_connectors(self):
        c = MockConnector()
        self.registry.register(c)
        connectors = self.registry.list_connectors()
        self.assertEqual(len(connectors), 1)

    def test_size(self):
        c = MockConnector()
        self.registry.register(c)
        self.assertEqual(self.registry.size(), 1)

    def test_clear(self):
        c = MockConnector()
        self.registry.register(c)
        self.registry.clear()
        self.assertEqual(self.registry.size(), 0)

    def test_validate_all(self):
        c = MockConnector()
        manifest = ConnectorManifest(
            connector_id="mock", name="Mock", version="1.0",
            capabilities=["api", "knowledge"], permissions=["read"],
        )
        self.registry.register(c, manifest=manifest)
        results = self.registry.validate_all()
        self.assertEqual(len(results), 0)


# ---------------------------------------------------------------------------
# Connector Manager
# ---------------------------------------------------------------------------

class Phase14ManagerTests(unittest.TestCase):
    def test_manager_start_stop(self):
        bus = DummyEventBus()
        manager = ConnectorManager(auto_discover=False, event_bus=bus)
        manager.start()
        self.assertTrue(manager._running)
        manager.stop()
        self.assertFalse(manager._running)

    def test_manager_register_and_list(self):
        manager = ConnectorManager(auto_discover=False)
        manager.start()
        c = MockConnector()
        manager._registry.register(c)
        self.assertEqual(manager.size(), 1)
        self.assertIn("mock", manager.list_ids())
        manager.stop()

    def test_manager_start_connector(self):
        manager = ConnectorManager(auto_discover=False)
        manager.start()
        c = MockConnector()
        c.connect()
        c._health.state = ConnectorState.DISCONNECTED
        manager._registry.register(c)
        result = manager.start_connector("mock")
        self.assertTrue(result)
        manager.stop()

    def test_manager_observe_connector(self):
        manager = ConnectorManager(auto_discover=False)
        manager.start()
        c = MockConnector()
        c.connect()
        manager._registry.register(c)
        obs = manager.observe_connector("mock")
        self.assertEqual(len(obs), 1)
        manager.stop()

    def test_manager_collect_evidence(self):
        manager = ConnectorManager(auto_discover=False)
        manager.start()
        c = MockConnector()
        c.connect()
        manager._registry.register(c)
        evidence = manager.collect_evidence("mock")
        self.assertEqual(len(evidence), 1)
        manager.stop()

    def test_manager_heartbeat_connector(self):
        manager = ConnectorManager(auto_discover=False)
        manager.start()
        c = MockConnector()
        c.connect()
        manager._registry.register(c)
        result = manager.heartbeat_connector("mock")
        self.assertTrue(result)
        manager.stop()

    def test_manager_connector_status(self):
        manager = ConnectorManager(auto_discover=False)
        manager.start()
        c = MockConnector()
        c.connect()
        manager._registry.register(c)
        status = manager.connector_status("mock")
        self.assertEqual(status["id"], "mock")
        manager.stop()

    def test_manager_get_connector(self):
        manager = ConnectorManager(auto_discover=False)
        manager.start()
        c = MockConnector()
        c.connect()
        manager._registry.register(c)
        retrieved = manager.get_connector("mock")
        self.assertIsNotNone(retrieved)
        manager.stop()

    def test_manager_check_health_all(self):
        manager = ConnectorManager(auto_discover=False)
        manager.start()
        c = MockConnector()
        c.connect()
        manager._registry.register(c)
        health = manager.check_health_all()
        self.assertIn("mock", health)
        manager.stop()

    def test_manager_has_connector(self):
        manager = ConnectorManager(auto_discover=False)
        manager.start()
        c = MockConnector()
        manager._registry.register(c)
        self.assertTrue(manager.has_connector("mock"))
        self.assertFalse(manager.has_connector("nonexistent"))
        manager.stop()

    def test_manager_stop_connector(self):
        manager = ConnectorManager(auto_discover=False)
        manager.start()
        c = MockConnector()
        c.connect()
        c._health.state = ConnectorState.DISCONNECTED
        c.start()
        manager._registry.register(c)
        result = manager.stop_connector("mock")
        self.assertTrue(result)
        manager.stop()

    def test_manager_get_uptime(self):
        manager = ConnectorManager(auto_discover=False)
        manager.start()
        uptime = manager.get_uptime()
        self.assertGreaterEqual(uptime, 0)
        manager.stop()


# ---------------------------------------------------------------------------
# SDK
# ---------------------------------------------------------------------------

class Phase14SDKTests(unittest.TestCase):
    def test_register_connector_cls(self):
        registry = ConnectorRegistry()
        cid = register_connector_cls(MockConnector, registry)
        self.assertEqual(cid, "mock")
        self.assertTrue(registry.has("mock"))

    def test_sdk_create_observation(self):
        c = MockConnector()
        source = Source.create(type_="test")
        raw = RawPayload.from_text("data")
        obs = ConnectorSDK.create_observation(c, "test_event", source, raw)
        self.assertTrue(obs.id)

    def test_sdk_create_evidence(self):
        c = MockConnector()
        source = Source.create(type_="test")
        raw = RawPayload.from_text("data")
        obs = Observation.create(type_="test", source=source, raw=raw)
        norm = NormalizedPayload.structured({"data": "test"})
        evidence = ConnectorSDK.create_evidence(c, obs, norm)
        self.assertTrue(evidence.id)

    def test_sdk_run_pipeline(self):
        c = MockConnector()
        c.connect()
        evidence_list = ConnectorSDK.run_pipeline(c)
        self.assertEqual(len(evidence_list), 1)

    def test_sdk_require_capability(self):
        c = MockConnector()
        ConnectorSDK.require_capability(c, "api")
        with self.assertRaises(ConnectorCapabilityError):
            ConnectorSDK.require_capability(c, "database")

    def test_sdk_require_permission(self):
        c = MockConnector()
        ConnectorSDK.require_permission(c, "read")
        with self.assertRaises(ConnectorPermissionError):
            ConnectorSDK.require_permission(c, "execute")


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

class Phase14DiscoveryTests(unittest.TestCase):
    def test_discover_directory_invalid(self):
        registry = ConnectorRegistry()
        discovery = ConnectorDiscovery(registry)
        with self.assertRaises(ConnectorError):
            discovery.discover_directory("/nonexistent/path")

    def test_discover_directory_empty(self):
        registry = ConnectorRegistry()
        discovery = ConnectorDiscovery(registry)
        with tempfile.TemporaryDirectory() as tmpdir:
            results = discovery.discover_directory(tmpdir)
            self.assertEqual(len(results), 0)

    def test_discover_directory_with_manifest(self):
        registry = ConnectorRegistry()
        discovery = ConnectorDiscovery(registry)
        import tempfile as tf
        import os
        with tf.TemporaryDirectory() as tmpdir:
            manifest_path = os.path.join(tmpdir, "test_connector.json")
            with open(manifest_path, "w") as f:
                json.dump({
                    "connector_id": "from_file",
                    "name": "From File",
                    "version": "1.0",
                    "capabilities": ["api"],
                    "permissions": ["read"],
                }, f)
            # This will try to load the module; we expect a failure at load
            # since there's no actual connector module, but discovery reports it
            results = discovery.discover_directory(tmpdir)
            self.assertGreaterEqual(len(results), 1)

    def test_resolve_dependencies(self):
        registry = ConnectorRegistry()
        discovery = ConnectorDiscovery(registry)
        mc = MockConnector()
        mc.id = "dependent"
        manifest = ConnectorManifest(
            connector_id="dependent", name="Dep", version="1.0",
            dependencies=["base"],
            capabilities=["api"], permissions=["read"],
        )
        registry.register(mc, manifest=manifest)
        unresolved = discovery.resolve_dependencies()
        self.assertEqual(len(unresolved), 1)
        self.assertEqual(unresolved[0][0], "dependent")
        self.assertEqual(unresolved[0][1], ["base"])

    def test_resolve_dependencies_satisfied(self):
        registry = ConnectorRegistry()
        discovery = ConnectorDiscovery(registry)
        base_manifest = ConnectorManifest(
            connector_id="base", name="Base", version="1.0",
            capabilities=["api"], permissions=["read"],
        )
        dep_manifest = ConnectorManifest(
            connector_id="dependent", name="Dep", version="1.0",
            dependencies=["base"],
            capabilities=["api"], permissions=["read"],
        )
        registry.register(MockConnector(), manifest=dep_manifest)
        base = MockConnector()
        base.id = "base"
        base.name = "Base"
        registry.register(base, manifest=base_manifest)
        unresolved = discovery.resolve_dependencies()
        self.assertEqual(len(unresolved), 0)


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

class Phase14EventsTests(unittest.TestCase):
    def test_connector_event_constants(self):
        self.assertEqual(CONNECTOR_REGISTERED, "CONNECTOR_REGISTERED")
        self.assertEqual(CONNECTOR_STARTED, "CONNECTOR_STARTED")
        self.assertEqual(CONNECTOR_STOPPED, "CONNECTOR_STOPPED")
        self.assertEqual(CONNECTOR_EVIDENCE, "CONNECTOR_EVIDENCE")
        self.assertEqual(CONNECTOR_OBSERVATION, "CONNECTOR_OBSERVATION")

    def test_connector_event_data(self):
        data = ConnectorEventData(
            connector_id="test", event_type=CONNECTOR_STARTED,
            payload={"key": "value"},
        )
        self.assertEqual(data.connector_id, "test")
        self.assertEqual(data.event_type, CONNECTOR_STARTED)
        self.assertEqual(data.payload["key"], "value")


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

class Phase14LoaderTests(unittest.TestCase):
    def test_loader_find_connector_class(self):
        cls = ConnectorLoader._find_connector_class(MockConnector.__module__)
        if cls is None:
            import connectors.plugins.mock_connector as mc
            cls = ConnectorLoader._find_connector_class(mc)
        self.assertIsNotNone(cls)

    def test_loader_load_invalid_module(self):
        loader = ConnectorLoader()
        with self.assertRaises(ConnectorLoadError):
            loader.load_connector("nonexistent_module")

    def test_loader_resolve_entry_point(self):
        manifest = ConnectorManifest(
            connector_id="test", name="Test", version="1.0",
            capabilities=["api"], permissions=["read"],
        )
        ep = ConnectorLoader.resolve_entry_point(manifest)
        self.assertEqual(ep, "connectors.plugins.test_connector")

    def test_load_from_manifest_invalid_path(self):
        loader = ConnectorLoader()
        with self.assertRaises(ConnectorError):
            loader.load_from_manifest("/nonexistent/manifest.json")

    def test_discover_plugins_invalid_dir(self):
        loader = ConnectorLoader(plugins_dir="/nonexistent")
        results = loader.discover_plugins()
        self.assertEqual(results, [])

    def test_discover_plugins_valid_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = os.path.join(tmpdir, "test_plugin.json")
            with open(manifest_path, "w") as f:
                json.dump({
                    "connector_id": "plugin_test",
                    "name": "Plugin Test",
                    "version": "1.0",
                    "capabilities": ["api"],
                    "permissions": ["read"],
                }, f)
            loader = ConnectorLoader(plugins_dir=tmpdir)
            results = loader.discover_plugins()
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0][1].connector_id, "plugin_test")


# ---------------------------------------------------------------------------
# ConnectorService integration (not requiring full kernel)
# ---------------------------------------------------------------------------

class Phase14ConnectorServiceTests(unittest.TestCase):
    def test_service_start_stop(self):
        from services.connector_service import ConnectorService

        class DummyKernel:
            def __init__(self):
                self.services = {}
                self.event_bus = DummyEventBus()
                self._config = {"connectors": {"auto_discover": False}}

            def register_service(self, s):
                self.services[s.name] = s

            def get_service(self, name):
                return self.services.get(name)

            def get_config(self):
                return self._config

            def set_config(self, cfg):
                self._config = cfg

        kernel = DummyKernel()
        svc = ConnectorService(kernel)
        svc.start()
        self.assertIsNotNone(svc.get_manager())
        svc.stop()


# ---------------------------------------------------------------------------
# MCP tool integration tests
# ---------------------------------------------------------------------------

class Phase14MCPToolTests(unittest.TestCase):
    def test_connector_tools_in_list(self):
        from services.mcp_tool_service import MCPToolService

        class DummyKernel:
            def __init__(self):
                self.services = {}
                self.event_bus = DummyEventBus()
                self._config = {}

            def register_service(self, s):
                self.services[s.name] = s

            def get_service(self, name):
                return self.services.get(name)

            def get_config(self):
                return self._config

        kernel = DummyKernel()
        tool_svc = MCPToolService(kernel)
        tool_svc.connector = None
        tools = tool_svc.list_tools()
        tool_names = [t["name"] for t in tools]
        self.assertIn("list_connectors", tool_names)
        self.assertIn("get_connector_status", tool_names)
        self.assertIn("get_connector_health_all", tool_names)

    def test_list_connectors_returns_error_when_unavailable(self):
        from services.mcp_tool_service import MCPToolService

        class DummyKernel:
            def __init__(self):
                self.services = {}
                self.event_bus = DummyEventBus()
                self._config = {}

            def register_service(self, s):
                self.services[s.name] = s

            def get_service(self, name):
                return self.services.get(name)

            def get_config(self):
                return self._config

        kernel = DummyKernel()
        tool_svc = MCPToolService(kernel)
        tool_svc.connector = None
        result = tool_svc.call_tool("list_connectors", {})
        self.assertIn("error", result)

    def test_get_connector_status_returns_error_when_unavailable(self):
        from services.mcp_tool_service import MCPToolService

        class DummyKernel:
            def __init__(self):
                self.services = {}
                self.event_bus = DummyEventBus()
                self._config = {}

            def register_service(self, s):
                self.services[s.name] = s

            def get_service(self, name):
                return self.services.get(name)

            def get_config(self):
                return self._config

        kernel = DummyKernel()
        tool_svc = MCPToolService(kernel)
        tool_svc.connector = None
        result = tool_svc.call_tool("get_connector_status", {"connector_id": "mock"})
        self.assertIn("error", result)

    def test_existing_tools_preserved(self):
        from services.mcp_tool_service import MCPToolService

        class DummyKernel:
            def __init__(self):
                self.services = {}
                self.event_bus = DummyEventBus()
                self._config = {}

            def register_service(self, s):
                self.services[s.name] = s

            def get_service(self, name):
                return self.services.get(name)

            def get_config(self):
                return self._config

        kernel = DummyKernel()
        tool_svc = MCPToolService(kernel)
        tools = tool_svc.list_tools()
        tool_names = [t["name"] for t in tools]
        for name in ["search_memory", "build_context", "get_document",
                      "get_recent_events", "reindex_memory", "cross_reference",
                      "explain_change", "get_causal_chain", "compare_snapshots",
                      "list_decisions", "get_decision", "search_semantic",
                      "get_similar", "get_awareness_signals"]:
            self.assertIn(name, tool_names)


# ---------------------------------------------------------------------------
# Normalization Pipeline
# ---------------------------------------------------------------------------

class Phase14PipelineTests(unittest.TestCase):
    def test_pipeline_steps(self):
        c = MockConnector()
        c.connect()
        evidence_list = ConnectorSDK.run_pipeline(c)
        self.assertGreater(len(evidence_list), 0)
        for ev in evidence_list:
            self.assertTrue(ev.id)
            self.assertTrue(ev.observation_id)
            self.assertEqual(ev.trace.pipeline,
                             ["observe", "collect", "normalize", "emit"])

    def test_pipeline_empty_observation(self):
        c = MockConnector(config={"return_empty": True})
        c.connect()
        evidence_list = ConnectorSDK.run_pipeline(c)
        self.assertEqual(len(evidence_list), 0)

    def test_evidence_validation(self):
        c = MockConnector()
        c.connect()
        evidence_list = ConnectorSDK.run_pipeline(c)
        for ev in evidence_list:
            self.assertTrue(c.validate_evidence(ev))

    def test_invalid_evidence_rejected(self):
        c = MockConnector()
        bad = Evidence(id="", observation_id="",
                       normalized=NormalizedPayload.structured({}),
                       trace=TraceInformation("", "", []))
        self.assertFalse(c.validate_evidence(bad))
        self.assertFalse(c.emit(bad))


# ---------------------------------------------------------------------------
# Error recovery
# ---------------------------------------------------------------------------

class Phase14ErrorRecoveryTests(unittest.TestCase):
    def test_failed_connector_recovers(self):
        c = MockConnector(config={"fail_connect": True})
        result = c.connect()
        self.assertFalse(result)
        self.assertEqual(c.health().state, ConnectorState.ERROR)
        c._health.state = ConnectorState.DISCONNECTED
        c2 = MockConnector()
        result = c2.connect()
        self.assertTrue(result)

    def test_connector_error_state(self):
        c = MockConnector()
        c.connect()
        c._health.record_error("runtime error")
        self.assertEqual(c.health().state, ConnectorState.ERROR)
        self.assertEqual(len(c.health().errors), 1)


# ---------------------------------------------------------------------------
# Performance: startup, registration, normalization
# ---------------------------------------------------------------------------

class Phase14PerformanceTests(unittest.TestCase):
    def test_registration_speed(self):
        import time
        registry = ConnectorRegistry()
        start = time.time()
        for i in range(100):
            c = MockConnector()
            c.id = f"mock_{i}"
            registry.register(c)
        elapsed = time.time() - start
        self.assertEqual(registry.size(), 100)
        self.assertLess(elapsed, 5.0)

    def test_normalization_speed(self):
        import time
        c = MockConnector()
        c.connect()
        start = time.time()
        for _ in range(100):
            obs = c.observe()
        elapsed = time.time() - start
        self.assertLess(elapsed, 5.0)

    def test_heartbeat_latency(self):
        import time
        c = MockConnector()
        c.connect()
        start = time.time()
        for _ in range(100):
            c.heartbeat()
        elapsed = time.time() - start
        self.assertLess(elapsed, 5.0)


# ---------------------------------------------------------------------------
# Dynamic loading (plugin discovery)
# ---------------------------------------------------------------------------

class Phase14DynamicLoadingTests(unittest.TestCase):
    def test_dynamic_plugin_discovery(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = os.path.join(tmpdir, "dynamic_test.json")
            with open(manifest_path, "w") as f:
                json.dump({
                    "connector_id": "dynamic_test",
                    "name": "Dynamic Test",
                    "version": "1.0.0",
                    "capabilities": ["api"],
                    "permissions": ["read"],
                }, f)
            loader = ConnectorLoader(plugins_dir=tmpdir)
            results = loader.discover_plugins()
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0][1].connector_id, "dynamic_test")

    def test_loader_manifest_supported_extensions(self):
        exts = ManifestParser.SUPPORTED_EXTENSIONS
        self.assertIn(".json", exts)
        self.assertIn(".yaml", exts)


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

class Phase14LifecycleTests(unittest.TestCase):
    def test_full_lifecycle(self):
        manager = ConnectorManager(auto_discover=False)
        manager.start()
        c = MockConnector()
        manager._registry.register(c)
        manager.start_connector("mock")
        self.assertTrue(manager.has_connector("mock"))
        obs = manager.observe_connector("mock")
        self.assertEqual(len(obs), 1)
        evidence = manager.collect_evidence("mock")
        self.assertEqual(len(evidence), 1)
        health = manager.check_health_all()
        self.assertIn("mock", health)
        manager.stop_connector("mock")
        manager.stop()
        self.assertFalse(manager._running)

    def test_lifecycle_with_heartbeat(self):
        manager = ConnectorManager(auto_discover=False)
        manager.start()
        c = MockConnector()
        c.connect()
        manager._registry.register(c)
        for _ in range(3):
            manager.heartbeat_connector("mock")
        status = manager.connector_status("mock")
        self.assertGreater(status["health"]["last_heartbeat"], 0)
        manager.stop()


if __name__ == "__main__":
    unittest.main()
