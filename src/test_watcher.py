import time

from core.kernel import EyeKernel

from services.config_service import ConfigService
from services.logger_service import LoggerService
from services.mirror_service import MirrorService
from services.memory_service import MemoryService
from services.semantic_memory_service import SemanticMemoryService
from services.reflection_service import ReflectionService
from services.memory_query_service import MemoryQueryService
from services.memory_reindex_service import MemoryReindexService
from services.context_builder_service import ContextBuilderService
from services.vision_service import VisionService
from services.vision_memory_service import VisionMemoryService
from services.memory_gateway_service import MemoryGatewayService
from services.brain_service import BrainService
from services.knowledge_store_service import KnowledgeStoreService
from services.knowledge_indexer_service import KnowledgeIndexerService
from services.retrieval_service import RetrievalService
from services.knowledge_graph_service import KnowledgeGraphService
from services.reasoning_service import ReasoningService
from services.mcp_tool_service import MCPToolService
from services.cross_reference_service import CrossReferenceService
from services.symbol_indexer_service import SymbolIndexerService
from services.architecture_analyzer_service import ArchitectureAnalyzerService
from services.documentation_link_service import DocumentationLinkService

from watcher.watcher_service import WatcherService



kernel = EyeKernel()



config = ConfigService(kernel)

logger = LoggerService(kernel)

mirror = MirrorService(kernel)

memory = MemoryService(kernel)

semantic = SemanticMemoryService(kernel)

reflection = ReflectionService(kernel)

query = MemoryQueryService(kernel)

reindex = MemoryReindexService(kernel)

context = ContextBuilderService(kernel)

vision = VisionService(kernel)

vision_memory = VisionMemoryService(kernel)

brain = BrainService(kernel)

knowledge_store = KnowledgeStoreService(kernel)

indexer = KnowledgeIndexerService(kernel)

retrieval = RetrievalService(kernel)

graph = KnowledgeGraphService(kernel)

symbol_indexer = SymbolIndexerService(kernel)

cross_reference = CrossReferenceService(kernel)

architecture = ArchitectureAnalyzerService(kernel)

documentation = DocumentationLinkService(kernel)

reasoning = ReasoningService(kernel)

mcp_tools = MCPToolService(kernel)

gateway = MemoryGatewayService(kernel)

watcher = WatcherService(kernel)




kernel.register_service(config)

kernel.register_service(logger)

kernel.register_service(mirror)

kernel.register_service(memory)

kernel.register_service(semantic)

kernel.register_service(reflection)

kernel.register_service(query)

kernel.register_service(reindex)

kernel.register_service(context)

kernel.register_service(vision)

kernel.register_service(vision_memory)

kernel.register_service(brain)

kernel.register_service(knowledge_store)

kernel.register_service(symbol_indexer)

kernel.register_service(graph)

kernel.register_service(indexer)

kernel.register_service(retrieval)

kernel.register_service(cross_reference)

kernel.register_service(architecture)

kernel.register_service(documentation)

kernel.register_service(reasoning)

kernel.register_service(mcp_tools)

kernel.register_service(gateway)

kernel.register_service(watcher)




kernel.start()



# Upgrade old memories
reindex.reindex()



try:

    while True:

        time.sleep(1)



except KeyboardInterrupt:


    watcher.stop()

    gateway.stop()

    brain.stop()

    mcp_tools.stop()

    reasoning.stop()

    cross_reference.stop()

    documentation.stop()

    architecture.stop()

    graph.stop()

    symbol_indexer.stop()

    retrieval.stop()

    indexer.stop()

    knowledge_store.stop()

    vision_memory.stop()

    vision.stop()

    context.stop()

    reindex.stop()

    query.stop()

    reflection.stop()

    semantic.stop()

    memory.stop()

    mirror.stop()

    logger.stop()

    config.stop()
