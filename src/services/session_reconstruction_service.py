"""Replayable session views assembled only from cited timeline evidence."""

from services.service import Service


class SessionReconstructionService(Service):
    """Creates bounded, evidence-only engineering session reconstructions."""

    def __init__(self, kernel):
        super().__init__(kernel)
        self.timeline = None

    def start(self):
        super().start()
        self.timeline = self.kernel.get_service("TimelineService")
        if not self.timeline:
            raise RuntimeError("SessionReconstructionService requires TimelineService.")

    def reconstruct(self, session_id, start=None, end=None, limit=1000):
        """Return a replay sequence without inferring intent between events."""
        events = self.timeline.events(start=start, end=end, limit=limit)
        replay = [{
            "step": event["sequence"],
            "observed_at": event["observed_at"],
            "event_type": event["event_type"],
            "path": event["path"],
            "citation": event["citation"],
        } for event in events]
        return {
            "session_id": str(session_id),
            "replay": replay,
            "timeline": self.timeline.session_summary(start=start, end=end, limit=limit),
            "evidence": [step["citation"] for step in replay],
            "limitations": (
                "This reconstruction contains only recorded observable events; "
                "it does not claim hidden reasoning, unrecorded terminal activity, "
                "or unobserved actions."
            ),
        }
