"""Confidence Engine — scoring, evidence quality, and reasoning traces.

Every reasoning result shall expose a confidence score derived from evidence
quality, count, completeness, and consistency. No unsupported conclusions.
"""

from services.service import Service


class ConfidenceEngine(Service):
    def __init__(self, kernel):
        super().__init__(kernel)
        self.store = None

    def start(self):
        super().start()
        self.store = self.kernel.get_service("KnowledgeStoreService")
        if not self.store:
            raise RuntimeError("ConfidenceEngine requires KnowledgeStoreService.")

    def score_evidence(self, evidence_list):
        if not evidence_list:
            return 0.0, {"count": 0, "quality": 0.0, "missing": ["no evidence"], "trace": []}
        scores = []
        qualities = []
        sources = set()
        for ev in evidence_list:
            score = getattr(ev, "score", 1.0) if not isinstance(ev, dict) else ev.get("score", 1.0)
            scores.append(score)
            quality = self._assess_quality(ev)
            qualities.append(quality)
            src = getattr(ev, "connector_id", None) if not isinstance(ev, dict) else ev.get("connector_id")
            if src:
                sources.add(src)
        avg_score = sum(scores) / len(scores)
        avg_quality = sum(qualities) / len(qualities)
        coverage = len(sources) / max(len(sources), 1) if sources else 0.0
        final = avg_score * 0.4 + avg_quality * 0.4 + min(coverage, 1.0) * 0.2
        missing = self._detect_missing(evidence_list)
        trace = self._build_trace(evidence_list)
        return round(final, 2), {
            "count": len(evidence_list),
            "quality": round(avg_quality, 2),
            "coverage": round(coverage, 2),
            "sources": list(sources),
            "missing": missing,
            "trace": trace,
        }

    def score_relationships(self, relationships):
        if not relationships:
            return 0.0, {"count": 0, "trace": []}
        weighted = []
        for rel in relationships:
            meta = rel.get("metadata", {}) if isinstance(rel, dict) else {}
            weight = meta.get("weight", 1.0) if isinstance(meta, dict) else 1.0
            weighted.append(weight)
        avg_weight = sum(weighted) / len(weighted)
        trace = [{"type": "relationship", "count": len(weighted), "avg_weight": round(avg_weight, 2)}]
        final = min(avg_weight, 1.0)
        return round(final, 2), {"count": len(weighted), "avg_weight": round(avg_weight, 2), "trace": trace}

    def aggregate(self, *scores_and_details):
        if not scores_and_details:
            return 0.0, {"sub_scores": [], "combined": 0.0, "missing": ["no input"]}
        total = 0.0
        details = []
        for s, d in scores_and_details:
            if s is not None:
                total += s
                details.append(d)
        count = len(details) or 1
        combined = round(total / count, 2)
        return combined, {"sub_scores": details, "combined": combined}

    def _assess_quality(self, evidence):
        if isinstance(evidence, dict):
            has_citation = bool(evidence.get("citation") or evidence.get("id"))
            has_source = bool(evidence.get("connector_id") or evidence.get("source"))
            has_timestamp = bool(evidence.get("timestamp") or evidence.get("created_at"))
        else:
            has_citation = bool(getattr(evidence, "citation", None) or getattr(evidence, "id", None))
            has_source = bool(getattr(evidence, "connector_id", None))
            has_timestamp = bool(getattr(evidence, "timestamp", None) or getattr(evidence, "created_at", None))
        score = 0.0
        if has_citation:
            score += 0.4
        if has_source:
            score += 0.3
        if has_timestamp:
            score += 0.3
        return score

    def _detect_missing(self, evidence_list):
        missing = []
        if not evidence_list:
            missing.append("no evidence")
            return missing
        has_citation = False
        has_source = False
        has_timestamp = False
        for ev in evidence_list:
            if isinstance(ev, dict):
                if ev.get("citation") or ev.get("id"):
                    has_citation = True
                if ev.get("connector_id") or ev.get("source"):
                    has_source = True
                if ev.get("timestamp") or ev.get("created_at"):
                    has_timestamp = True
            else:
                if getattr(ev, "citation", None) or getattr(ev, "id", None):
                    has_citation = True
                if getattr(ev, "connector_id", None):
                    has_source = True
                if getattr(ev, "timestamp", None) or getattr(ev, "created_at", None):
                    has_timestamp = True
        if not has_citation:
            missing.append("missing citations")
        if not has_source:
            missing.append("missing source connector")
        if not has_timestamp:
            missing.append("missing timestamps")
        return missing

    def _build_trace(self, evidence_list):
        trace = []
        for i, ev in enumerate(evidence_list):
            if isinstance(ev, dict):
                eid = ev.get("citation") or ev.get("id") or "evidence:%d" % i
            else:
                eid = getattr(ev, "citation", None) or getattr(ev, "id", None) or "evidence:%d" % i
            trace.append({"evidence_id": eid, "index": i})
        return trace
