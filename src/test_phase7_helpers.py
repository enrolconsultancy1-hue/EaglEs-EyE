import tempfile

from core.kernel import EyeKernel
from services.context_builder_service import ContextBuilderService
from services.cross_reference_service import CrossReferenceService
from services.knowledge_graph_service import KnowledgeGraphService
from services.knowledge_indexer_service import KnowledgeIndexerService
from services.knowledge_store_service import KnowledgeStoreService
from services.retrieval_service import RetrievalService
from services.symbol_indexer_service import SymbolIndexerService
from services.architecture_analyzer_service import ArchitectureAnalyzerService
from services.documentation_link_service import DocumentationLinkService


class IntelligenceHarness:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory()
        self.kernel = EyeKernel()
        self.kernel.set_config({"memory_path": self.temp.name, "chunk_size": 128, "chunk_overlap": 16, "max_index_bytes": 1024 * 1024})
        self.store = KnowledgeStoreService(self.kernel)
        self.graph = KnowledgeGraphService(self.kernel)
        self.symbol_indexer = SymbolIndexerService(self.kernel)
        self.indexer = KnowledgeIndexerService(self.kernel)
        self.retrieval = RetrievalService(self.kernel)
        self.context = ContextBuilderService(self.kernel)
        self.cross_reference = CrossReferenceService(self.kernel)
        self.architecture = ArchitectureAnalyzerService(self.kernel)
        self.documentation = DocumentationLinkService(self.kernel)
        self.services = (self.store, self.symbol_indexer, self.graph, self.indexer, self.retrieval, self.context, self.cross_reference, self.architecture, self.documentation)
        for service in self.services:
            self.kernel.register_service(service)
            service.start()

    def close(self):
        for service in reversed(self.services):
            service.stop()
        self.temp.cleanup()
