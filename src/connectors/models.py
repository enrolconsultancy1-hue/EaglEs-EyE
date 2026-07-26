import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Timestamp:
    value: float
    source: str = "system"

    @classmethod
    def now(cls, source: str = "system"):
        return cls(value=time.time(), source=source)


@dataclass
class Identity:
    id: str
    name: str = ""
    type: str = ""

    @classmethod
    def create(cls, name: str = "", type_: str = ""):
        return cls(id=str(uuid.uuid4()), name=name, type=type_)


@dataclass
class Source:
    id: str
    type: str
    path: str = ""
    version: str = ""

    @classmethod
    def create(cls, type_: str, path: str = "", version: str = ""):
        return cls(id=str(uuid.uuid4()), type=type_, path=path, version=version)


@dataclass
class Artifact:
    id: str
    type: str
    content: str = ""
    path: str = ""
    mime_type: str = ""
    size: int = 0

    @classmethod
    def create(cls, type_: str, content: str = "", path: str = "",
               mime_type: str = ""):
        return cls(
            id=str(uuid.uuid4()), type=type_, content=content,
            path=path, mime_type=mime_type, size=len(content),
        )


@dataclass
class Relationship:
    source_id: str
    target_id: str
    type: str
    metadata: dict = field(default_factory=dict)


@dataclass
class Confidence:
    score: float
    method: str = "direct"

    @classmethod
    def certain(cls):
        return cls(score=1.0, method="direct")

    @classmethod
    def derived(cls, score: float = 0.8):
        return cls(score=score, method="derived")


@dataclass
class Metadata:
    key: str
    value: Any
    namespace: str = "connector"


@dataclass
class RawPayload:
    data: Any
    format: str = "raw"
    size: int = 0

    @classmethod
    def from_text(cls, text: str):
        return cls(data=text, format="text", size=len(text))

    @classmethod
    def from_dict(cls, data: dict):
        import json
        raw = json.dumps(data)
        return cls(data=data, format="json", size=len(raw))


@dataclass
class NormalizedPayload:
    data: Any
    format: str = "structured"
    schema_version: str = "1.0"

    @classmethod
    def structured(cls, data: dict):
        return cls(data=data, format="structured", schema_version="1.0")


@dataclass
class TraceInformation:
    connector_id: str
    connector_version: str
    pipeline: list
    duration_ms: float = 0.0


@dataclass
class CitationInformation:
    sources: list = field(default_factory=list)
    evidence_ids: list = field(default_factory=list)
    confidence: Confidence = field(default_factory=Confidence.certain)


@dataclass
class Observation:
    id: str
    type: str
    timestamp: Timestamp
    source: Source
    raw: RawPayload
    metadata: dict = field(default_factory=dict)

    @classmethod
    def create(cls, type_: str, source: Source, raw: RawPayload,
               metadata: dict = None):
        return cls(
            id=str(uuid.uuid4()), type=type_,
            timestamp=Timestamp.now(source="connector"),
            source=source, raw=raw, metadata=metadata or {},
        )


@dataclass
class Evidence:
    id: str
    observation_id: str
    normalized: NormalizedPayload
    artifacts: list = field(default_factory=list)
    relationships: list = field(default_factory=list)
    identities: list = field(default_factory=list)
    citations: CitationInformation = field(default_factory=CitationInformation)
    trace: TraceInformation = field(default_factory=lambda: TraceInformation("", "", []))
    confidence: Confidence = field(default_factory=Confidence.certain)
    metadata: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    @classmethod
    def create(cls, observation: Observation, normalized: NormalizedPayload,
               trace: TraceInformation, artifacts: list = None,
               relationships: list = None, identities: list = None,
               citations: CitationInformation = None,
               confidence: Confidence = None):
        return cls(
            id=str(uuid.uuid4()),
            observation_id=observation.id,
            normalized=normalized,
            artifacts=artifacts or [],
            relationships=relationships or [],
            identities=identities or [],
            citations=citations or CitationInformation(),
            trace=trace,
            confidence=confidence or Confidence.certain(),
        )
