import os
import json
from datetime import datetime

from services.service import Service


class MemoryService(Service):

    def __init__(self, kernel):

        super().__init__(kernel)

        # Configuration is loaded later by ConfigService.
        self.memory_path = None

        self.memory_file = None


    def start(self):

        super().start()

        config = self.kernel.get_config()

        self.memory_path = config.get(
            "memory_path",
            "memory"
        )

        self.memory_file = os.path.join(
            self.memory_path,
            "memory.json"
        )

        os.makedirs(
            self.memory_path,
            exist_ok=True
        )

        if not os.path.exists(
            self.memory_file
        ):
            self._create_memory()

        self.kernel.event_bus.subscribe(
            "FILE_CREATED",
            self.remember_created
        )

        self.kernel.event_bus.subscribe(
            "FILE_MODIFIED",
            self.remember_modified
        )

        self.kernel.event_bus.subscribe(
            "FILE_DELETED",
            self.remember_deleted
        )


    def stop(self):

        super().stop()


    def remember_created(self, data):

        self.remember(
            "FILE_CREATED",
            data
        )


    def remember_modified(self, data):

        self.remember(
            "FILE_MODIFIED",
            data
        )


    def remember_deleted(self, data):

        self.remember(
            "FILE_DELETED",
            data
        )


    def remember(self, event_type, data):

        path = data.get(
            "path",
            ""
        ).lower()

        # Never remember internal runtime files.
        if "memory" in path:
            return

        if "mirror" in path:
            return

        memory = self._load_memory()

        memory.append(
            {
                "timestamp": datetime.now().isoformat(),
                "event": event_type,
                "data": data
            }
        )

        with open(
            self.memory_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                memory,
                f,
                indent=4
            )

        print(
            f"[MEMORY] Stored: {event_type}"
        )


    def _create_memory(self):

        with open(
            self.memory_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                [],
                f,
                indent=4
            )


    def _load_memory(self):

        try:

            with open(
                self.memory_file,
                "r",
                encoding="utf-8"
            ) as f:

                return json.load(f)

        except Exception:

            return []