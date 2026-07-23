from services.service import Service


class LoggerService(Service):

    def start(self):

        super().start()

        self.kernel.event_bus.subscribe(
            "FILE_CREATED",
            self.file_created
        )

        self.kernel.event_bus.subscribe(
            "FILE_MODIFIED",
            self.file_modified
        )

        self.kernel.event_bus.subscribe(
            "FILE_DELETED",
            self.file_deleted
        )


    def file_created(self, data):
        print(
            f"[LOGGER] CREATED: {data['path']}"
        )


    def file_modified(self, data):
        print(
            f"[LOGGER] MODIFIED: {data['path']}"
        )


    def file_deleted(self, data):
        print(
            f"[LOGGER] DELETED: {data['path']}"
        )