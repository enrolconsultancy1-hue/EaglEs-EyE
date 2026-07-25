import hashlib
import mimetypes
import os
import queue
import threading

from services.service import Service


class KnowledgeIndexerService(Service):
    """Queues filesystem events and incrementally creates versioned records."""

    TEXT_EXTENSIONS = {".txt", ".md", ".py", ".js", ".json", ".yaml", ".yml", ".csv"}

    def __init__(self, kernel):
        super().__init__(kernel)
        self.store = None
        self.graph = None
        self.symbol_indexer = None
        self.tasks = queue.Queue()
        self.worker = None
        self.running = False
        self.chunk_size = 1200
        self.chunk_overlap = 200
        self.max_index_bytes = 5 * 1024 * 1024
        self.verbose = False

    def start(self):
        super().start()
        self.store = self.kernel.get_service("KnowledgeStoreService")
        self.graph = self.kernel.get_service("KnowledgeGraphService")
        self.symbol_indexer = self.kernel.get_service("SymbolIndexerService")
        if not self.store:
            raise RuntimeError("KnowledgeIndexerService requires KnowledgeStoreService.")
        config = self.kernel.get_config()
        self.chunk_size = max(100, int(config.get("chunk_size", self.chunk_size)))
        self.chunk_overlap = min(self.chunk_size - 1, max(0, int(config.get("chunk_overlap", self.chunk_overlap))))
        self.max_index_bytes = max(1, int(config.get("max_index_bytes", self.max_index_bytes)))
        self.verbose = bool(config.get("verbose_indexing", False))
        self.running = True
        self.worker = threading.Thread(target=self._run, name="knowledge-indexer", daemon=True)
        self.worker.start()
        for event_name in ("FILE_CREATED", "FILE_MODIFIED", "FILE_DELETED"):
            self.kernel.event_bus.subscribe(event_name, self.enqueue)
        print("[INDEXER] Ready.")

    def stop(self):
        self.running = False
        if self.worker:
            self.tasks.put(None)
            self.worker.join(timeout=5)
            self.worker = None
        super().stop()

    def enqueue(self, data):
        self.tasks.put(dict(data or {}))

    def wait_until_idle(self):
        self.tasks.join()

    def reindex_path(self, path):
        self.tasks.put({"path": os.path.abspath(path), "event_type": "REINDEX"})

    def _run(self):
        while self.running:
            data = self.tasks.get()
            try:
                if data is None:
                    return
                self._index(data)
            except Exception as error:
                print("[INDEXER] Failed:", error)
            finally:
                self.tasks.task_done()

    def _index(self, data):
        path = os.path.abspath(data.get("path", ""))
        event_type = data.get("event_type", "FILE_MODIFIED")
        if not path:
            return
        self.store.record_event(event_type, path, data)
        if event_type == "FILE_DELETED" or not os.path.exists(path):
            self.store.upsert_document(path, "", None, None, 0, "watcher", {"event_type": event_type}, "deleted")
            return
        if not os.path.isfile(path):
            return
        extension = os.path.splitext(path)[1].lower()
        mime_type, _ = mimetypes.guess_type(path)
        stat = os.stat(path)
        oversized = stat.st_size > self.max_index_bytes
        content = self._read_text(path) if extension in self.TEXT_EXTENSIONS and not oversized else ""
        content_hash = self._sha256(path) if not oversized else "oversized:%s:%s" % (stat.st_size, stat.st_mtime_ns)
        document_id, version, changed = self.store.upsert_document(
            path, content, content_hash, mime_type, stat.st_size, "watcher",
            {"extension": extension, "filename": os.path.basename(path), "folder": os.path.dirname(path),
             "category": self._category(extension), "event_type": event_type},
        )
        if changed and content:
            self.store.add_chunks(document_id, version, self._chunk(content))
        if changed and self.symbol_indexer and extension == ".py":
            self.symbol_indexer.index_document(path)
        if changed and self.graph and extension == ".py":
            self.graph.analyze_document(path)
        if self.verbose:
            print("[INDEXER] Indexed:", os.path.basename(path))

    @staticmethod
    def _category(extension):
        if extension in {".py", ".js"}:
            return "code"
        if extension in {".json", ".yaml", ".yml"}:
            return "configuration"
        if extension in {".txt", ".md", ".csv"}:
            return "knowledge"
        return "media" if extension else "unknown"

    def _read_text(self, path):
        try:
            with open(path, "r", encoding="utf-8") as source:
                return source.read()
        except (OSError, UnicodeDecodeError):
            return ""

    def _sha256(self, path):
        digest = hashlib.sha256()
        with open(path, "rb") as source:
            for block in iter(lambda: source.read(65536), b""):
                digest.update(block)
        return digest.hexdigest()

    def _chunk(self, content):
        chunks = []
        offset = 0
        while offset < len(content):
            end = min(len(content), offset + self.chunk_size)
            if end < len(content):
                boundary = content.rfind("\n", offset, end)
                if boundary > offset:
                    end = boundary + 1
            text = content[offset:end]
            chunks.append({"offset": offset, "text": text, "hash": hashlib.sha256(text.encode("utf-8")).hexdigest()})
            if end >= len(content):
                break
            offset = max(end - self.chunk_overlap, offset + 1)
        return chunks
