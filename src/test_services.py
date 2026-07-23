from core.kernel import EyeKernel
from watcher.watcher_service import WatcherService
from services.logger_service import LoggerService

kernel = EyeKernel()

logger = LoggerService(kernel)
watcher = WatcherService(kernel)

kernel.register_service(logger)
kernel.register_service(watcher)

kernel.start()