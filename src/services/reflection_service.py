from services.service import Service
from datetime import datetime


class ReflectionService(Service):

    def __init__(self, kernel):

        super().__init__(kernel)

        self.events = []
        self.store = None


    def start(self):

        super().start()

        self.store = self.kernel.get_service(
            "KnowledgeStoreService"
        )

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

    def summary(self):
        """Return and persist an auditable, non-autonomous health reflection."""
        statistics = self.store.statistics() if self.store else {}
        result = {
            "events_observed": len(self.events),
            "knowledge": statistics,
            "message": "Reflection is observational only; no files were modified."
        }
        if self.store:
            self.store.record_reflection("Knowledge health summary", result)
        return result

    def repository_health(self, documentation=None, architecture=None):
        statistics = self.store.statistics() if self.store else {}
        health = {"services": len(self.store.find_symbols("Service", 1000)) if self.store else 0,
                  "symbols": statistics.get("symbols", 0), "relationships": statistics.get("relationships", 0),
                  "documentation_coverage": (documentation or {}).get("coverage"),
                  "circular_dependencies": len((architecture or {}).get("circular_dependencies", [])),
                  "duplicate_symbols": len((architecture or {}).get("duplicate_symbols", [])),
                  "knowledge_freshness": "available"}
        if self.store: self.store.record_reflection("Repository health snapshot", health)
        return health
