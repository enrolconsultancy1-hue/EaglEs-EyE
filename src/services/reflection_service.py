from services.service import Service
from datetime import datetime


class ReflectionService(Service):

    def __init__(self, kernel):

        super().__init__(kernel)

        self.events = []


    def start(self):

        super().start()

        self.kernel.event_bus.subscribe(
            "FILE_CREATED",
            self.observe
        )

        self.kernel.event_bus.subscribe(
            "FILE_MODIFIED",
            self.observe
        )

        self.kernel.event_bus.subscribe(
            "FILE_DELETED",
            self.observe
        )


    def stop(self):

        super().stop()



    def observe(self, data):

        self.events.append(
            {
                "time": datetime.now().isoformat(),
                "data": data
            }
        )


        self.reflect()



    def reflect(self):

        total = len(self.events)


        print(
            f"[REFLECTION] Events observed: {total}"
        )