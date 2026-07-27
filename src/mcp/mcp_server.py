"""MCP JSON-RPC 2.0 server — initialize, tools/list, tools/call with structured errors."""

import contextlib
import json
import os
import sys
import tempfile

from core.kernel import EyeKernel
from mcp.tool_registry import ToolRegistry
from mcp.transport_stdio import read_message, write_message
from mcp.transport_tcp import TcpTransport
from services.architecture_analyzer_service import ArchitectureAnalyzerService
from services.architecture_evolution_service import ArchitectureEvolutionService
from services.causal_graph_service import CausalGraphService
from services.cognitive_layer_service import CognitiveLayerService
from services.context_builder_service import ContextBuilderService
from services.cross_reference_service import CrossReferenceService
from services.decision_tracking_service import DecisionTrackingService
from services.documentation_link_service import DocumentationLinkService
from services.embedding_service import EmbeddingService
from services.execution_timeline_service import ExecutionTimelineService
from services.knowledge_graph_service import KnowledgeGraphService
from services.knowledge_indexer_service import KnowledgeIndexerService
from services.knowledge_store_service import KnowledgeStoreService
from services.mcp_tool_service import MCPToolService
from services.retrieval_service import RetrievalService
from services.semantic_awareness_service import SemanticAwarenessService
from services.session_recorder_service import SessionRecorderService
from services.symbol_indexer_service import SymbolIndexerService
from services.vector_search_service import VectorSearchService
from services.workspace_observer_service import WorkspaceObserverService
from services.connector_service import ConnectorService
from services.connector_scheduler_service import ConnectorSchedulerService
from services.evidence_ingestion_service import EvidenceIngestionService
from services.confidence_engine import ConfidenceEngine
from services.reasoning_engine import ReasoningEngine
from services.project_intelligence_engine import ProjectIntelligenceEngine
from services.root_cause_analysis_service import RootCauseAnalysisService
from services.impact_analysis_service import ImpactAnalysisService
from services.decision_lineage_service import DecisionLineageService
from services.explainable_ai_service import ExplainableAIService
from services.ai_twin_orchestrator import AITwinOrchestrator
from services.twin_integrity_validator import TwinIntegrityValidator
from services.unified_project_twin import UnifiedProjectTwin
from services.universal_twin_report import UniversalTwinReport
from services.project_twin_discovery_service import ProjectTwinDiscoveryService


SUPPORTED_PROTOCOL_VERSION = "2025-03-26"


class MCPServer:
    def __init__(self, tool_registry=None):
        self.registry = tool_registry or ToolRegistry()
        self._initialized = False

    def handle_message(self, raw_msg):
        if isinstance(raw_msg, dict) and "error" in raw_msg:
            return None
        if not isinstance(raw_msg, dict) or "jsonrpc" not in raw_msg:
            return self._error(None, -32600, "Invalid Request: must be valid JSON-RPC 2.0 message")
        if raw_msg.get("jsonrpc") != "2.0":
            return self._error(raw_msg.get("id"), -32600, "Invalid Request: jsonrpc must be '2.0'")
        method = raw_msg.get("method", "")
        msg_id = raw_msg.get("id")
        params = raw_msg.get("params", {})
        if method == "initialize":
            return self._handle_initialize(msg_id, params)
        if not self._initialized:
            return self._error(msg_id, -32000, "Server not initialized")
        if method == "tools/list":
            return self._handle_tools_list(msg_id, params)
        if method == "tools/call":
            return self._handle_tools_call(msg_id, params)
        return self._error(msg_id, -32601, "Method not found: " + method)

    def _handle_initialize(self, msg_id, params):
        self._initialized = True
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": SUPPORTED_PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "EaglEs EyE MCP", "version": "3.0.0"},
            },
        }

    def _handle_tools_list(self, msg_id, params):
        tools = self.registry.list_tools()
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": tools}}

    def _handle_tools_call(self, msg_id, params):
        name = params.get("name", "")
        arguments = params.get("arguments", {})
        result = self.registry.call_tool(name, arguments)
        if isinstance(result, dict) and "error" in result:
            return self._error(msg_id, result.get("code", -32603), result["error"])
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"content": [{"type": "text", "text": json.dumps(result, default=str)}]}}

    @staticmethod
    def _error(msg_id, code, message):
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}

    def run_stdio(self):
        while True:
            msg = read_message()
            if msg is None:
                break
            response = self.handle_message(msg)
            if response is not None:
                write_message(response)

    def run_once(self, msg_dict):
        return self.handle_message(msg_dict)


def build_mcp_kernel(memory_path=None):
    kernel = EyeKernel()
    if memory_path:
        kernel.set_config({"memory_path": memory_path})
    store = KnowledgeStoreService(kernel)
    sym_idx = SymbolIndexerService(kernel)
    kg = KnowledgeGraphService(kernel)
    indexer = KnowledgeIndexerService(kernel)
    retrieval = RetrievalService(kernel)
    ctx = ContextBuilderService(kernel)
    xref = CrossReferenceService(kernel)
    arch = ArchitectureAnalyzerService(kernel)
    docs = DocumentationLinkService(kernel)
    ws = WorkspaceObserverService(kernel)
    timeline = ExecutionTimelineService(kernel)
    sessions = SessionRecorderService(kernel)
    causal = CausalGraphService(kernel)
    evolution = ArchitectureEvolutionService(kernel)
    decisions = DecisionTrackingService(kernel)
    cognitive = CognitiveLayerService(kernel)
    embedding = EmbeddingService(kernel)
    vector_search = VectorSearchService(kernel)
    awareness = SemanticAwarenessService(kernel)
    connector_svc = ConnectorService(kernel)
    evidence_ingestion = EvidenceIngestionService(kernel)
    connector_scheduler = ConnectorSchedulerService(kernel)
    confidence_engine = ConfidenceEngine(kernel)
    reasoning_engine = ReasoningEngine(kernel)
    project_intelligence = ProjectIntelligenceEngine(kernel)
    root_cause = RootCauseAnalysisService(kernel)
    impact = ImpactAnalysisService(kernel)
    decision_lineage = DecisionLineageService(kernel)
    explainable = ExplainableAIService(kernel)
    ai_twin = AITwinOrchestrator(kernel)
    twin_validator = TwinIntegrityValidator(kernel)
    unified_twin = UnifiedProjectTwin(kernel)
    twin_report = UniversalTwinReport(kernel)
    project_twin = ProjectTwinDiscoveryService(kernel)
    mcp_tool = MCPToolService(kernel)
    services = (store, sym_idx, kg, indexer, retrieval, ctx, xref, arch, docs,
                ws, timeline, sessions, causal, evolution, decisions, cognitive,
                embedding, vector_search, awareness, connector_svc,
                evidence_ingestion, connector_scheduler,
                confidence_engine, reasoning_engine, project_intelligence,
                root_cause, impact, decision_lineage, explainable,
                ai_twin, twin_validator, unified_twin, twin_report,
                project_twin,
                mcp_tool)
    for s in services:
        kernel.register_service(s)
        s.start()
    return kernel, services


def main():
    memory_path = os.environ.get("EAGLE_EYE_MEMORY_PATH")
    if not memory_path:
        tmp = tempfile.TemporaryDirectory()
        memory_path = tmp.name
    with contextlib.redirect_stdout(sys.stderr):
        kernel, services = build_mcp_kernel(memory_path)
        mcp_tool = kernel.get_service("MCPToolService")
        registry = ToolRegistry()
        for tool in mcp_tool.list_tools():
            name = tool["name"]
            schema = tool["inputSchema"]
            def make_fn(tool_name):
                return lambda **kw: mcp_tool.call_tool(tool_name, kw)
            registry.register(name, make_fn(name), schema, tool.get("description", ""))
        server = MCPServer(registry)
        config = kernel.get_config() or {}
        tcp_transport = None
        if config.get("mcp", {}).get("tcp", {}).get("enabled", False):
            host = config["mcp"]["tcp"].get("host", "127.0.0.1")
            port = config["mcp"]["tcp"].get("port", 9102)
            tcp_transport = TcpTransport(host, port)
            tcp_transport.start(server.handle_message)
    # Redirect stdout → stderr for the process lifetime so that
    # EventBus.publish() and other print() calls don't corrupt the
    # JSON-RPC protocol stream (write_message uses _PROTOCOL_STDOUT
    # captured at import in transport_stdio.py).
    sys.stdout = sys.stderr
    try:
        server.run_stdio()
    finally:
        if tcp_transport:
            tcp_transport.stop()
        for s in reversed(services):
            s.stop()


if __name__ == "__main__":
    main()
