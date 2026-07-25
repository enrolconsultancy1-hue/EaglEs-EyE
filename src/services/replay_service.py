"""Evidence-based replay from persisted local twin artifacts."""

import json
import os

from services.service import Service


class ReplayService(Service):
    def replay(self, twin_path):
        with open(os.path.join(twin_path, "timeline.json"), encoding="utf-8") as source: timeline = json.load(source)
        with open(os.path.join(twin_path, "summary.json"), encoding="utf-8") as source: summary = json.load(source)
        return {"replay": timeline, "summary": summary, "evidence": [item["citation"] for item in timeline], "scope": "Observable evidence only; no hidden reasoning is claimed."}
