"""SQLite persistence for EaglEs EyE's durable knowledge model.

The store is intentionally independent of watchers and transports.  JSON
memory files remain supported by their existing services while this becomes
the transactional source for indexed documents and retrieval.
"""

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone

from services.service import Service


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class KnowledgeStoreService(Service):
    def __init__(self, kernel):
        super().__init__(kernel)
        self.database_path = None
        self.connection = None
        self.lock = threading.RLock()

    def start(self):
        super().start()
        config = self.kernel.get_config()
        memory_path = config.get("memory_path", "memory")
        os.makedirs(memory_path, exist_ok=True)
        self.database_path = os.path.join(memory_path, "knowledge.db")
        self.connection = sqlite3.connect(self.database_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        # WAL permits readers while the index worker commits. NORMAL is safe
        # for atomic SQLite transactions and avoids a filesystem sync per event.
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=NORMAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute("PRAGMA busy_timeout=5000")
        self._create_schema()
        self._import_legacy_knowledge(os.path.join(memory_path, "knowledge.json"))
        print("[KNOWLEDGE STORE] Ready:", self.database_path)

    def stop(self):
        if self.connection:
            self.connection.close()
            self.connection = None
        super().stop()

    @contextmanager
    def transaction(self):
        if not self.connection:
            raise RuntimeError("KnowledgeStoreService has not been started.")
        with self.lock:
            try:
                yield self.connection
                self.connection.commit()
            except Exception:
                self.connection.rollback()
                raise

    def _create_schema(self):
        statements = (
            """CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE, hash TEXT,
                mime_type TEXT, size INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                deleted_at TEXT, status TEXT NOT NULL, source TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}', version INTEGER NOT NULL DEFAULT 0
            )""",
            """CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY, document_id INTEGER NOT NULL,
                version INTEGER NOT NULL, offset INTEGER NOT NULL, length INTEGER NOT NULL,
                text TEXT NOT NULL, hash TEXT NOT NULL, embedding_id TEXT,
                active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL,
                UNIQUE(document_id, version, offset),
                FOREIGN KEY(document_id) REFERENCES documents(id)
            )""",
            """CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY, event_type TEXT NOT NULL, path TEXT,
                payload TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS workspaces (
                id TEXT PRIMARY KEY, path TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'active', metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active', metadata TEXT NOT NULL DEFAULT '{}',
                started_at TEXT NOT NULL, ended_at TEXT,
                FOREIGN KEY(workspace_id) REFERENCES workspaces(id)
            )""",
            """CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY, document_id INTEGER, kind TEXT NOT NULL,
                payload TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL,
                FOREIGN KEY(document_id) REFERENCES documents(id)
            )""",
            """CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY, chunk_id INTEGER NOT NULL, provider TEXT NOT NULL,
                model TEXT, vector TEXT NOT NULL, created_at TEXT NOT NULL,
                FOREIGN KEY(chunk_id) REFERENCES chunks(id)
            )""",
            """CREATE TABLE IF NOT EXISTS reflections (
                id INTEGER PRIMARY KEY, summary TEXT NOT NULL, payload TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS retrieval_logs (
                id INTEGER PRIMARY KEY, query TEXT NOT NULL, filters TEXT NOT NULL DEFAULT '{}',
                result_count INTEGER NOT NULL, created_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY, source_document_id INTEGER NOT NULL,
                target_path TEXT NOT NULL, relation TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL,
                UNIQUE(source_document_id, target_path, relation),
                FOREIGN KEY(source_document_id) REFERENCES documents(id)
            )""",
            """CREATE TABLE IF NOT EXISTS symbols (
                id INTEGER PRIMARY KEY, document_id INTEGER NOT NULL,
                version INTEGER NOT NULL, name TEXT NOT NULL, qualname TEXT NOT NULL,
                kind TEXT NOT NULL, module TEXT, parent_symbol TEXT,
                line INTEGER, end_line INTEGER, line_start INTEGER, line_end INTEGER,
                docstring TEXT, visibility TEXT, signature TEXT,
                metadata TEXT NOT NULL DEFAULT '{}', active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                UNIQUE(document_id, version, qualname, kind, line),
                FOREIGN KEY(document_id) REFERENCES documents(id)
            )""",
            "CREATE INDEX IF NOT EXISTS idx_chunks_active ON chunks(active, document_id)",
            "CREATE INDEX IF NOT EXISTS idx_events_path ON events(path)",
            "CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_document_id)",
            "CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name, active)",
            """CREATE TABLE IF NOT EXISTS causal_edges (
                id INTEGER PRIMARY KEY, source_event_id INTEGER NOT NULL,
                target_event_id INTEGER NOT NULL, relation_type TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL,
                UNIQUE(source_event_id, target_event_id, relation_type)
            )""",
            """CREATE TABLE IF NOT EXISTS decision_records (
                id INTEGER PRIMARY KEY, workspace_id TEXT,
                session_id TEXT, decision_type TEXT NOT NULL,
                summary TEXT NOT NULL, evidence_citations TEXT NOT NULL DEFAULT '[]',
                payload TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS architecture_snapshots (
                id INTEGER PRIMARY KEY, workspace_id TEXT NOT NULL,
                session_id TEXT, label TEXT, symbol_data TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )""",
        )
        with self.transaction() as connection:
            for statement in statements:
                connection.execute(statement)
            # Existing Phase 7 databases receive these richer symbol columns
            # without losing their historical records.
            for column, definition in (
                ("module", "TEXT"), ("parent_symbol", "TEXT"),
                ("docstring", "TEXT"), ("visibility", "TEXT"),
                ("line_start", "INTEGER"), ("line_end", "INTEGER"),
                ("workspace_id", "TEXT"), ("session_id", "TEXT"),
            ):
                table = "events" if column in ("workspace_id", "session_id") else "symbols"
                self._ensure_column(connection, table, column, definition)
            connection.execute("CREATE INDEX IF NOT EXISTS idx_events_workspace ON events(workspace_id, session_id)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_sessions_workspace ON sessions(workspace_id, started_at)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_causal_source ON causal_edges(source_event_id)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_causal_target ON causal_edges(target_event_id)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_decision_workspace ON decision_records(workspace_id)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_snapshot_workspace ON architecture_snapshots(workspace_id)")

    @staticmethod
    def _ensure_column(connection, table, column, definition):
        columns = {row[1] for row in connection.execute("PRAGMA table_info(" + table + ")")}
        if column not in columns:
            connection.execute("ALTER TABLE " + table + " ADD COLUMN " + column + " " + definition)

    def _import_legacy_knowledge(self, legacy_path):
        """Import old JSON once without replacing the compatibility file."""
        if not os.path.exists(legacy_path):
            return
        with self.transaction() as connection:
            imported = connection.execute(
                "SELECT 1 FROM observations WHERE kind = 'legacy_import' LIMIT 1"
            ).fetchone()
        if imported:
            return
        try:
            with open(legacy_path, encoding="utf-8") as source:
                records = json.load(source)
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(records, dict):
            return
        for path, item in records.items():
            self.upsert_document(
                path=path,
                content=item.get("content") or "",
                content_hash=item.get("sha256"),
                mime_type=item.get("mime"),
                size=item.get("size", 0),
                source="legacy_json",
                metadata={key: value for key, value in item.items() if key != "content"},
                status=item.get("status", "active"),
            )
        with self.transaction() as connection:
            connection.execute(
                "INSERT INTO observations(kind, payload, created_at) VALUES (?, ?, ?)",
                ("legacy_import", json.dumps({"path": legacy_path}), utc_now()),
            )

    def upsert_document(self, path, content, content_hash, mime_type, size, source,
                        metadata=None, status="active"):
        now = utc_now()
        metadata_json = json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True)
        with self.transaction() as connection:
            existing = connection.execute(
                "SELECT * FROM documents WHERE path = ?", (path,)
            ).fetchone()
            if existing and existing["hash"] == content_hash and existing["status"] == status:
                connection.execute(
                    "UPDATE documents SET updated_at = ?, metadata = ? WHERE id = ?",
                    (now, metadata_json, existing["id"]),
                )
                return existing["id"], existing["version"], False
            if existing:
                version = existing["version"] + 1
                connection.execute("UPDATE chunks SET active = 0 WHERE document_id = ? AND active = 1", (existing["id"],))
                connection.execute(
                    """UPDATE documents SET hash=?, mime_type=?, size=?, updated_at=?, deleted_at=?,
                    status=?, source=?, metadata=?, version=? WHERE id=?""",
                    (content_hash, mime_type, size, now, now if status == "deleted" else None,
                     status, source, metadata_json, version, existing["id"]),
                )
                return existing["id"], version, True
            cursor = connection.execute(
                """INSERT INTO documents(path, hash, mime_type, size, created_at, updated_at,
                deleted_at, status, source, metadata, version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                (path, content_hash, mime_type, size, now, now,
                 now if status == "deleted" else None, status, source, metadata_json),
            )
            return cursor.lastrowid, 1, True

    def add_chunks(self, document_id, version, chunks):
        if not chunks:
            return
        with self.transaction() as connection:
            connection.executemany(
                """INSERT OR IGNORE INTO chunks(document_id, version, offset, length, text, hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [(document_id, version, item["offset"], len(item["text"]), item["text"], item["hash"], utc_now())
                 for item in chunks],
            )

    def record_event(self, event_type, path, payload, workspace_id=None, session_id=None):
        with self.transaction() as connection:
            connection.execute(
                """INSERT INTO events(event_type, path, payload, created_at, workspace_id, session_id)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (event_type, path, json.dumps(payload or {}, ensure_ascii=False), utc_now(), workspace_id, session_id),
            )

    def upsert_workspace(self, workspace_id, path, metadata=None, status="active"):
        now = utc_now()
        metadata_json = json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True)
        with self.transaction() as connection:
            connection.execute(
                """INSERT INTO workspaces(id, path, status, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET path=excluded.path, status=excluded.status,
                metadata=excluded.metadata, updated_at=excluded.updated_at""",
                (workspace_id, path, status, metadata_json, now, now),
            )
            row = connection.execute("SELECT * FROM workspaces WHERE id = ?", (workspace_id,)).fetchone()
        return self._workspace_row(row)

    def set_workspace_status(self, workspace_id, status):
        with self.transaction() as connection:
            connection.execute(
                "UPDATE workspaces SET status = ?, updated_at = ? WHERE id = ?",
                (status, utc_now(), workspace_id),
            )
            row = connection.execute("SELECT * FROM workspaces WHERE id = ?", (workspace_id,)).fetchone()
        return self._workspace_row(row) if row else None

    def list_workspaces(self, include_inactive=True):
        query = "SELECT * FROM workspaces"
        parameters = ()
        if not include_inactive:
            query += " WHERE status = ?"
            parameters = ("active",)
        query += " ORDER BY path"
        with self.transaction() as connection:
            rows = [self._workspace_row(row) for row in connection.execute(query, parameters)]
        return rows

    def get_workspace(self, workspace_id):
        with self.transaction() as connection:
            row = connection.execute("SELECT * FROM workspaces WHERE id = ?", (workspace_id,)).fetchone()
        return self._workspace_row(row) if row else None

    def create_session(self, session_id, workspace_id, metadata=None):
        now = utc_now()
        with self.transaction() as connection:
            connection.execute(
                """INSERT INTO sessions(id, workspace_id, status, metadata, started_at)
                VALUES (?, ?, 'active', ?, ?)""",
                (session_id, workspace_id, json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True), now),
            )
            row = connection.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return self._session_row(row)

    def close_session(self, session_id):
        with self.transaction() as connection:
            connection.execute("UPDATE sessions SET status = 'closed', ended_at = ? WHERE id = ?", (utc_now(), session_id))
            row = connection.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return self._session_row(row) if row else None

    def get_session(self, session_id):
        with self.transaction() as connection:
            row = connection.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return self._session_row(row) if row else None

    def list_sessions(self, workspace_id=None, active_only=False):
        clauses, parameters = [], []
        if workspace_id:
            clauses.append("workspace_id = ?"); parameters.append(workspace_id)
        if active_only:
            clauses.append("status = 'active'")
        query = "SELECT * FROM sessions" + (" WHERE " + " AND ".join(clauses) if clauses else "") + " ORDER BY started_at"
        with self.transaction() as connection:
            rows = [self._session_row(row) for row in connection.execute(query, parameters)]
        return rows

    def session_events(self, workspace_id=None, session_id=None, start=None, end=None):
        clauses, parameters = [], []
        for column, value in (("workspace_id", workspace_id), ("session_id", session_id)):
            if value:
                clauses.append(column + " = ?"); parameters.append(value)
        if start:
            clauses.append("created_at >= ?"); parameters.append(start)
        if end:
            clauses.append("created_at <= ?"); parameters.append(end)
        query = "SELECT * FROM events" + (" WHERE " + " AND ".join(clauses) if clauses else "") + " ORDER BY created_at, id"
        with self.transaction() as connection:
            return [dict(row) for row in connection.execute(query, parameters)]

    @staticmethod
    def _workspace_row(row):
        result = dict(row)
        result["metadata"] = json.loads(result["metadata"] or "{}")
        return result

    @staticmethod
    def _session_row(row):
        result = dict(row)
        result["metadata"] = json.loads(result["metadata"] or "{}")
        return result

    def record_reflection(self, summary, payload):
        with self.transaction() as connection:
            connection.execute(
                "INSERT INTO reflections(summary, payload, created_at) VALUES (?, ?, ?)",
                (summary, json.dumps(payload or {}, ensure_ascii=False), utc_now()),
            )

    def add_relationship(self, source_document_id, target_path, relation, metadata=None):
        with self.transaction() as connection:
            connection.execute(
                """INSERT INTO relationships(source_document_id, target_path, relation, metadata, created_at)
                VALUES (?, ?, ?, ?, ?) ON CONFLICT(source_document_id, target_path, relation)
                DO UPDATE SET metadata=excluded.metadata, created_at=excluded.created_at""",
                (source_document_id, target_path, relation,
                 json.dumps(metadata or {}, ensure_ascii=False), utc_now()),
            )

    def replace_symbols(self, document_id, version, symbols):
        """Version symbols with their document; old facts remain auditable."""
        with self.transaction() as connection:
            connection.execute("UPDATE symbols SET active = 0 WHERE document_id = ? AND active = 1", (document_id,))
            connection.executemany(
                """INSERT OR IGNORE INTO symbols(document_id, version, name, qualname, kind, module,
                parent_symbol, line, end_line, line_start, line_end, docstring, visibility, signature, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [(document_id, version, item["name"], item["qualname"], item["kind"],
                  item.get("module"), item.get("parent_symbol"), item.get("line"), item.get("end_line"),
                  item.get("line"), item.get("end_line"), item.get("docstring"), item.get("visibility"), item.get("signature"),
                  json.dumps(item.get("metadata", {}), ensure_ascii=False), utc_now()) for item in symbols],
            )

    def find_symbols(self, name, limit=30):
        with self.transaction() as connection:
            return [dict(row) for row in connection.execute(
                """SELECT symbols.*, symbols.id AS symbol_id, documents.path FROM symbols JOIN documents ON documents.id = symbols.document_id
                WHERE symbols.active = 1 AND symbols.name LIKE ? ORDER BY documents.path, symbols.line LIMIT ?""",
                ("%" + name + "%", limit),
            )]

    def symbol_history(self, document_id):
        with self.transaction() as connection:
            return [dict(row) for row in connection.execute(
                "SELECT *, id AS symbol_id FROM symbols WHERE document_id = ? ORDER BY version, line",
                (document_id,),
            )]

    def integrity_check(self):
        with self.transaction() as connection:
            return connection.execute("PRAGMA integrity_check").fetchone()[0]

    def get_document(self, path, include_chunks=True):
        with self.transaction() as connection:
            document = connection.execute("SELECT * FROM documents WHERE path = ?", (path,)).fetchone()
            if not document:
                return None
            result = dict(document)
            result["metadata"] = json.loads(result["metadata"])
            if include_chunks:
                result["chunks"] = [dict(row) for row in connection.execute(
                    "SELECT * FROM chunks WHERE document_id = ? AND active = 1 ORDER BY offset",
                    (document["id"],),
                )]
            return result

    def active_chunks(self):
        with self.transaction() as connection:
            return [dict(row) for row in connection.execute(
                """SELECT chunks.*, documents.path, documents.mime_type, documents.updated_at,
                documents.metadata, documents.status FROM chunks JOIN documents ON documents.id = chunks.document_id
                WHERE chunks.active = 1 AND documents.status = 'active'"""
            )]

    def recent_events(self, limit=10):
        with self.transaction() as connection:
            return [dict(row) for row in connection.execute(
                "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
            )]

    def add_causal_edge(self, source_event_id, target_event_id, relation_type, metadata=None):
        with self.transaction() as connection:
            connection.execute(
                """INSERT OR IGNORE INTO causal_edges(source_event_id, target_event_id, relation_type, metadata, created_at)
                VALUES (?, ?, ?, ?, ?)""",
                (source_event_id, target_event_id, relation_type,
                 json.dumps(metadata or {}, ensure_ascii=False), utc_now()),
            )
            row = connection.execute(
                "SELECT * FROM causal_edges WHERE source_event_id = ? AND target_event_id = ? AND relation_type = ?",
                (source_event_id, target_event_id, relation_type),
            ).fetchone()
        return dict(row) if row else None

    def get_causal_edges(self, event_id=None, relation_type=None):
        clauses, parameters = [], []
        if event_id:
            clauses.append("(source_event_id = ? OR target_event_id = ?)")
            parameters.extend([event_id, event_id])
        if relation_type:
            clauses.append("relation_type = ?")
            parameters.append(relation_type)
        query = "SELECT * FROM causal_edges" + (" WHERE " + " AND ".join(clauses) if clauses else "") + " ORDER BY created_at"
        with self.transaction() as connection:
            return [dict(row) for row in connection.execute(query, parameters)]

    def add_decision_record(self, workspace_id, session_id, decision_type, summary, evidence_citations=None, payload=None):
        with self.transaction() as connection:
            connection.execute(
                """INSERT INTO decision_records(workspace_id, session_id, decision_type, summary, evidence_citations, payload, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (workspace_id, session_id, decision_type, summary,
                 json.dumps(evidence_citations or [], ensure_ascii=False),
                 json.dumps(payload or {}, ensure_ascii=False), utc_now()),
            )
            return connection.execute("SELECT * FROM decision_records ORDER BY id DESC LIMIT 1").fetchone()["id"]

    def list_decision_records(self, workspace_id=None, session_id=None):
        clauses, parameters = [], []
        if workspace_id:
            clauses.append("workspace_id = ?"); parameters.append(workspace_id)
        if session_id:
            clauses.append("session_id = ?"); parameters.append(session_id)
        query = "SELECT * FROM decision_records" + (" WHERE " + " AND ".join(clauses) if clauses else "") + " ORDER BY created_at"
        with self.transaction() as connection:
            rows = [dict(row) for row in connection.execute(query, parameters)]
        for row in rows:
            row["evidence_citations"] = json.loads(row.get("evidence_citations") or "[]")
            row["payload"] = json.loads(row.get("payload") or "{}")
        return rows

    def save_architecture_snapshot(self, workspace_id, session_id, label, symbol_data):
        with self.transaction() as connection:
            connection.execute(
                """INSERT INTO architecture_snapshots(workspace_id, session_id, label, symbol_data, created_at)
                VALUES (?, ?, ?, ?, ?)""",
                (workspace_id, session_id, label,
                 json.dumps(symbol_data, ensure_ascii=False), utc_now()),
            )
            return connection.execute("SELECT * FROM architecture_snapshots ORDER BY id DESC LIMIT 1").fetchone()["id"]

    def get_architecture_snapshot(self, snapshot_id):
        with self.transaction() as connection:
            row = connection.execute("SELECT * FROM architecture_snapshots WHERE id = ?", (snapshot_id,)).fetchone()
            if not row:
                return None
            result = dict(row)
            result["symbol_data"] = json.loads(result["symbol_data"])
            return result

    def list_architecture_snapshots(self, workspace_id=None, session_id=None):
        clauses, parameters = [], []
        if workspace_id:
            clauses.append("workspace_id = ?"); parameters.append(workspace_id)
        if session_id:
            clauses.append("session_id = ?"); parameters.append(session_id)
        query = "SELECT * FROM architecture_snapshots" + (" WHERE " + " AND ".join(clauses) if clauses else "") + " ORDER BY created_at"
        with self.transaction() as connection:
            rows = [dict(row) for row in connection.execute(query, parameters)]
        for row in rows:
            row["symbol_data"] = json.loads(row["symbol_data"])
        return rows

    def get_event_by_id(self, event_id):
        with self.transaction() as connection:
            row = connection.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        return dict(row) if row else None

    def statistics(self):
        with self.transaction() as connection:
            return {
                "documents": connection.execute("SELECT COUNT(*) FROM documents WHERE status = 'active'").fetchone()[0],
                "chunks": connection.execute("SELECT COUNT(*) FROM chunks WHERE active = 1").fetchone()[0],
                "events": connection.execute("SELECT COUNT(*) FROM events").fetchone()[0],
                "reflections": connection.execute("SELECT COUNT(*) FROM reflections").fetchone()[0],
                "relationships": connection.execute("SELECT COUNT(*) FROM relationships").fetchone()[0],
                "symbols": connection.execute("SELECT COUNT(*) FROM symbols WHERE active = 1").fetchone()[0],
                "workspaces": connection.execute("SELECT COUNT(*) FROM workspaces WHERE status = 'active'").fetchone()[0],
                "sessions": connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0],
                "causal_edges": connection.execute("SELECT COUNT(*) FROM causal_edges").fetchone()[0],
                "decision_records": connection.execute("SELECT COUNT(*) FROM decision_records").fetchone()[0],
                "architecture_snapshots": connection.execute("SELECT COUNT(*) FROM architecture_snapshots").fetchone()[0],
            }
