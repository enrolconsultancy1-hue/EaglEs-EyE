import os
import shutil

from services.service import Service


class MirrorService(Service):

    def __init__(self, kernel):

        super().__init__(kernel)

        config = kernel.get_config()

        self.source = os.path.abspath(
            config.get(
                "watch_path",
                "workspace"
            )
        )

        self.destination = os.path.abspath(
            config.get(
                "mirror_path",
                "../EaglEs-EyE-data/mirror"
            )
        )


    def start(self):

        super().start()

        self.kernel.event_bus.subscribe(
            "FILE_CREATED",
            self.handle_create
        )

        self.kernel.event_bus.subscribe(
            "FILE_MODIFIED",
            self.handle_modify
        )

        self.kernel.event_bus.subscribe(
            "FILE_DELETED",
            self.handle_delete
        )

        os.makedirs(
            self.destination,
            exist_ok=True
        )


    def mirror_path(self, path):

        relative = os.path.relpath(
            os.path.abspath(path),
            self.source
        )

        return os.path.join(
            self.destination,
            relative
        )


    def handle_create(self, data):

        self.copy_file(
            data["path"]
        )


    def handle_modify(self, data):

        self.copy_file(
            data["path"]
        )


    def handle_delete(self, data):

        target = self.mirror_path(
            data["path"]
        )

        if os.path.exists(target):

            os.remove(target)

            print(
                "[MIRROR] Deleted:",
                target
            )


    def copy_file(self, source):

        source = os.path.abspath(source)

        if not os.path.isfile(source):
            return

        destination = self.mirror_path(source)

        os.makedirs(
            os.path.dirname(destination),
            exist_ok=True
        )

        shutil.copy2(
            source,
            destination
        )

        print(
            "[MIRROR]",
            source,
            "=>",
            destination
        )