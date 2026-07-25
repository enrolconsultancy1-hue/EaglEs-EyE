"""Multi-agent session, timeline, performance, and architecture comparison.

Operates strictly on observable durable event evidence, session metadata, and
workspace markers. Never infers hidden AI reasoning.
"""

from datetime import datetime
from services.service import Service


class MultiAgentObservationService(Service):
    def __init__(self, kernel):
        super().__init__(kernel)
        self.store = None
        self.timeline = None
        self.detector = None

    def start(self):
        super().start()
        self.store = self.kernel.get_service("KnowledgeStoreService")
        self.timeline = self.kernel.get_service("ExecutionTimelineService")
        self.detector = self.kernel.get_service("AgentDetectorService")
        if not self.store or not self.timeline:
            raise RuntimeError("MultiAgentObservationService requires KnowledgeStoreService and ExecutionTimelineService.")

    def compare_sessions(self, session_ids):
        """Compare multiple sessions across observable metrics and event history."""
        comparisons = []
        for session_id in session_ids:
            session = self.store.get_session(session_id)
            if not session:
                raise ValueError("Unknown session: %s" % session_id)
            events = self.timeline.events(session_id=session_id)
            event_types = {}
            files_touched = set()
            for event in events:
                et = event["event_type"]
                event_types[et] = event_types.get(et, 0) + 1
                if event.get("path"):
                    files_touched.add(event["path"])
            
            duration = None
            if session.get("started_at") and session.get("ended_at"):
                try:
                    start_dt = datetime.fromisoformat(session["started_at"])
                    end_dt = datetime.fromisoformat(session["ended_at"])
                    duration = (end_dt - start_dt).total_seconds()
                except Exception:
                    pass

            comparisons.append({
                "session": session,
                "event_count": len(events),
                "event_types": event_types,
                "files_touched": sorted(list(files_touched)),
                "citations": [event["citation"] for event in events],
                "duration_seconds": duration,
            })
        return {
            "sessions": comparisons,
            "scope": "Observable evidence only; no hidden reasoning is claimed.",
        }

    def compare_agents(self, workspace_paths):
        """Compare detected agents across multiple workspaces or session paths."""
        results = []
        for path in workspace_paths:
            detection = self.detector.detect(path) if self.detector else {"workspace": path, "agents": []}
            sessions = self.store.list_sessions(workspace_id=None) if self.store else []
            # Find sessions matching workspace path if possible
            matching_sessions = []
            for s in sessions:
                ws = self.store.get_workspace(s["workspace_id"])
                if ws and ws["path"] == path:
                    matching_sessions.append(s["id"])
            
            session_comparison = self.compare_sessions(matching_sessions) if matching_sessions else {"sessions": []}
            results.append({
                "workspace": path,
                "detection": detection,
                "sessions": session_comparison["sessions"],
            })
        return {
            "comparison": results,
            "scope": "Observable evidence only; no hidden reasoning is claimed.",
        }

    def compare_timelines(self, session_ids):
        """Align and compare timelines side-by-side from multiple sessions."""
        timelines = {}
        max_len = 0
        for session_id in session_ids:
            events = self.timeline.events(session_id=session_id)
            timelines[session_id] = events
            if len(events) > max_len:
                max_len = len(events)

        steps = []
        for i in range(max_len):
            step_entries = {}
            for session_id in session_ids:
                evs = timelines[session_id]
                step_entries[session_id] = evs[i] if i < len(evs) else None
            steps.append({"step": i + 1, "events": step_entries})

        return {
            "session_ids": session_ids,
            "max_steps": max_len,
            "steps": steps,
            "scope": "Observable event sequence only.",
        }

    def compare_performance(self, session_ids):
        """Compare performance indicators derived strictly from observed session evidence."""
        metrics = []
        for session_id in session_ids:
            session = self.store.get_session(session_id)
            events = self.timeline.events(session_id=session_id)
            duration = 0.0
            if session and session.get("started_at"):
                try:
                    start = datetime.fromisoformat(session["started_at"])
                    end = datetime.fromisoformat(session["ended_at"]) if session.get("ended_at") else datetime.now(timezone.utc)
                    duration = max(0.0, (end - start).total_seconds())
                except Exception:
                    pass

            test_success = 0
            test_failure = 0
            for event in events:
                if event["event_type"] in ("TEST_OBSERVED", "TEST_RUN"):
                    payload = event.get("payload", {})
                    if payload.get("exit_code") == 0:
                        test_success += 1
                    else:
                        test_failure += 1

            metrics.append({
                "session_id": session_id,
                "duration_seconds": duration,
                "event_count": len(events),
                "event_rate_per_sec": len(events) / duration if duration > 0 else float(len(events)),
                "test_success_count": test_success,
                "test_failure_count": test_failure,
            })
        return {
            "performance": metrics,
            "scope": "Observable execution metrics only.",
        }

    def compare_architecture(self, session_ids):
        """Compare structural/architectural impact (files and symbols touched) across sessions."""
        impacts = []
        for session_id in session_ids:
            events = self.timeline.events(session_id=session_id)
            files = set()
            event_types = set()
            for event in events:
                if event.get("path"):
                    files.add(event["path"])
                event_types.add(event["event_type"])
            impacts.append({
                "session_id": session_id,
                "files_touched": sorted(list(files)),
                "event_types_observed": sorted(list(event_types)),
            })
        return {
            "architecture_impact": impacts,
            "scope": "Observable file and event impact only.",
        }
