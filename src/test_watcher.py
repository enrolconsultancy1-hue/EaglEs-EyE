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

kernel.register_service(watcher)




kernel.start()



# Upgrade old memories
reindex.reindex()



try:

    while True:

        time.sleep(1)



except KeyboardInterrupt:


    watcher.stop()

    context.stop()

    reindex.stop()

    query.stop()

    reflection.stop()

    semantic.stop()

    memory.stop()

    mirror.stop()

    logger.stop()

    config.stop()