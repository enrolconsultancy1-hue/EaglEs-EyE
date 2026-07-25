"""Evidence-only timelines reconstructed from the durable event log."""

import json

from services.service import Service


class TimelineService(Service):
    """Read-only timeline and session summaries; it never infers hidden intent."""

    def __init__(self, kernel):
        super().__init__(kernel)
        self.store = None

    def start(self):
        super().start()
        self.store = self.kernel.get_service("KnowledgeStoreService")
        if not self.store:
            raise RuntimeError("TimelineService requires KnowledgeStoreService.")

    def events(self, start=None, end=None, limit=1000):
        """Return ordered, cited event evidence within an optional time range."""
        clauses, parameters = [], []
        if start:
            clauses.append("created_at >= ?")
            parameters.append(start)
        if end:
            clauses.append("created_at <= ?")
            parameters.append(end)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        parameters.append(max(1, int(limit)))
        with self.store.transaction() as connection:
            rows = [dict(row) for row in connection.execute(
                "SELECT id, event_type, path, payload, created_at FROM events" + where +
                " ORDER BY id ASC LIMIT ?", parameters
            )]
        return [{
            "sequence": index + 1,
            "event_id": row["id"],
            "event_type": row["event_type"],
            "path": row["path"],
            "payload": json.loads(row["payload"] or "{}"),
            "observed_at": row["created_at"],
            "citation": "event:%s" % row["id"],
        } for index, row in enumerate(rows)]

    def session_summary(self, start=None, end=None, limit=1000):
        """Summarize observable activity without attributing reasons or intent."""
        events = self.events(start=start, end=end, limit=limit)
        paths = sorted({event["path"] for event in events if event["path"]})
        event_types = {}
        for event in events:
            event_types[event["event_type"]] = event_types.get(event["event_type"], 0) + 1
        return {
            "event_count": len(events),
            "event_types": event_types,
            "affected_paths": paths,
            "first_observed_at": events[0]["observed_at"] if events else None,
            "last_observed_at": events[-1]["observed_at"] if events else None,
            "evidence": [event["citation"] for event in events],
            "scope": "Observable event evidence only; no hidden reasoning is claimed.",
        }
