import os

from services.service import Service

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from core.filter import EyeFilter



class EyeFileHandler(FileSystemEventHandler):


    def __init__(
        self,
        event_bus,
        eye_filter
    ):

        self.event_bus = event_bus

        self.eye_filter = eye_filter



    def process(
        self,
        event_type,
        path
    ):

        path = os.path.abspath(
            path
        )


        if not self.eye_filter.allowed(path):

            return



        self.event_bus.publish(
            event_type,
            {
                "path": path
            }
        )



    def on_created(
        self,
        event
    ):

        if not event.is_directory:

            self.process(
                "FILE_CREATED",
                event.src_path
            )



    def on_modified(
        self,
        event
    ):

        if not event.is_directory:

            self.process(
                "FILE_MODIFIED",
                event.src_path
            )



    def on_deleted(
        self,
        event
    ):

        if not event.is_directory:

            self.process(
                "FILE_DELETED",
                event.src_path
            )







class WatcherService(Service):


    def __init__(
        self,
        kernel
    ):

        super().__init__(
            kernel
        )


        self.observer = Observer()

        self.watch_path = None

        self.filter = None





    def start(self):

        super().start()



        config = self.kernel.get_config()



        self.watch_path = config.get(
            "watch_path",
            "."
        )



        ignored = config.get(
            "ignore",
            []
        )



        self.filter = EyeFilter(
            ignored
        )



        handler = EyeFileHandler(
            self.kernel.event_bus,
            self.filter
        )



        self.observer.schedule(
            handler,
            self.watch_path,
            recursive=True
        )



        self.observer.start()



        self.kernel.event_bus.publish(
            "WATCHER_STARTED",
            {
                "path": self.watch_path
            }
        )





    def stop(self):

        self.observer.stop()

        self.observer.join()

        super().stop()