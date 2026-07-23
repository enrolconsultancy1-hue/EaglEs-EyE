import time

from core.kernel import EyeKernel

from services.config_service import ConfigService
from services.logger_service import LoggerService
from services.mirror_service import MirrorService
from services.memory_service import MemoryService
from services.reflection_service import ReflectionService

from watcher.watcher_service import WatcherService


kernel = EyeKernel()


config = ConfigService(kernel)

logger = LoggerService(kernel)

mirror = MirrorService(kernel)

memory = MemoryService(kernel)

reflection = ReflectionService(kernel)

watcher = WatcherService(kernel)



kernel.register_service(config)

kernel.register_service(logger)

kernel.register_service(mirror)

kernel.register_service(memory)

kernel.register_service(reflection)

kernel.register_service(watcher)



kernel.start()



try:

    while True:

        time.sleep(1)


except KeyboardInterrupt:

    watcher.stop()

    reflection.stop()

    memory.stop()

    mirror.stop()

    logger.stop()

    config.stop()