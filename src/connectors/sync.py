"""Synchronization Engine — incremental sync, checkpoints, resume, conflict detection.

Supports initial sync, delta sync, checkpoints stored in the Knowledge Store,
resume from checkpoint, conflict detection, sync statistics, and failure recovery.
"""

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SyncCheckpoint:
    connector_id: str
    surface: str
    cursor: str = ""
    timestamp: float = 0.0
    completed: bool = False
    item_count: int = 0

    def to_dict(self) -> dict:
        return {
            "connector_id": self.connector_id,
            "surface": self.surface,
            "cursor": self.cursor,
            "timestamp": self.timestamp,
            "completed": self.completed,
            "item_count": self.item_count,
        }

    @staticmethod
    def from_dict(data: dict) -> "SyncCheckpoint":
        return SyncCheckpoint(
            connector_id=data.get("connector_id", ""),
            surface=data.get("surface", ""),
            cursor=data.get("cursor", ""),
            timestamp=data.get("timestamp", 0.0),
            completed=data.get("completed", False),
            item_count=data.get("item_count", 0),
        )


@dataclass
class SyncStatistics:
    connector_id: str = ""
    surface: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0
    items_synced: int = 0
    items_failed: int = 0
    api_requests: int = 0
    retries: int = 0
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "connector_id": self.connector_id,
            "surface": self.surface,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "items_synced": self.items_synced,
            "items_failed": self.items_failed,
            "api_requests": self.api_requests,
            "retries": self.retries,
            "duration_ms": self.duration_ms,
        }


class SyncStore:
    def __init__(self):
        self._checkpoints: dict[str, SyncCheckpoint] = {}

    def save_checkpoint(self, checkpoint: SyncCheckpoint):
        key = f"{checkpoint.connector_id}:{checkpoint.surface}"
        self._checkpoints[key] = checkpoint

    def load_checkpoint(self, connector_id: str, surface: str) -> Optional[SyncCheckpoint]:
        return self._checkpoints.get(f"{connector_id}:{surface}")

    def clear_checkpoint(self, connector_id: str, surface: str):
        self._checkpoints.pop(f"{connector_id}:{surface}", None)


class SyncEngine:
    def __init__(self, store: Optional[SyncStore] = None):
        self._store = store or SyncStore()
        self._statistics: list[SyncStatistics] = []

    def get_store(self):
        return self._store

    def initial_sync(self, connector_id: str, surface: str,
                     fetch_fn, cursor: str = "") -> SyncStatistics:
        stats = SyncStatistics(connector_id=connector_id, surface=surface,
                               started_at=time.time())
        all_items = []
        checkpoint = SyncCheckpoint(
            connector_id=connector_id, surface=surface,
            cursor=cursor, timestamp=time.time(),
        )
        try:
            page_cursor = cursor
            while True:
                result = fetch_fn(page_cursor)
                if not result:
                    break
                items, next_cursor, has_more = result
                all_items.extend(items)
                stats.api_requests += 1
                if not has_more:
                    break
                page_cursor = next_cursor
            checkpoint.item_count = len(all_items)
            checkpoint.completed = True
            checkpoint.cursor = page_cursor
        except Exception as e:
            checkpoint.item_count = len(all_items)
            checkpoint.cursor = page_cursor
            raise e
        finally:
            self._store.save_checkpoint(checkpoint)
            stats.completed_at = time.time()
            stats.duration_ms = (stats.completed_at - stats.started_at) * 1000
            stats.items_synced = len(all_items)
            self._statistics.append(stats)
        return stats, all_items

    def delta_sync(self, connector_id: str, surface: str,
                   fetch_fn) -> SyncStatistics:
        checkpoint = self._store.load_checkpoint(connector_id, surface)
        cursor = checkpoint.cursor if checkpoint else ""
        return self.initial_sync(connector_id, surface, fetch_fn, cursor=cursor)

    def resume(self, connector_id: str, surface: str,
               fetch_fn) -> Optional[SyncStatistics]:
        checkpoint = self._store.load_checkpoint(connector_id, surface)
        if not checkpoint:
            return None
        if checkpoint.completed:
            return None
        cursor = checkpoint.cursor or ""
        return self.initial_sync(connector_id, surface, fetch_fn, cursor=cursor)

    def detect_conflict(self, local_cursor: str, remote_cursor: str) -> bool:
        return local_cursor != remote_cursor

    def last_sync(self, connector_id: str, surface: str = "") -> Optional[dict]:
        for stat in reversed(self._statistics):
            if stat.connector_id == connector_id:
                if not surface or stat.surface == surface:
                    return stat.to_dict()
        return None

    def get_statistics(self, connector_id: str = "") -> list[dict]:
        if connector_id:
            return [s.to_dict() for s in self._statistics if s.connector_id == connector_id]
        return [s.to_dict() for s in self._statistics]
