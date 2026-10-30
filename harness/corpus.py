"""Local, source-traceable document inventory and SQLite search.

Source text is untrusted data. Indexing never executes source content. Literal
search is case sensitive and supports Korean and punctuation without tokenizing.
Regex searches run in an isolated process with a fixed wall-clock limit. FTS uses
SQLite FTS5 query syntax; it is optional and its tokenizer is not Korean morphology.
"""
from __future__ import annotations

from contextlib import closing
import datetime as dt
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from typing import Iterator

SUPPORTED_EXTENSIONS = frozenset({".txt", ".md", ".markdown", ".ndjson", ".csv", ".tsv", ".json", ".jsonl", ".pdf", ".docx", ".xlsx"})
EXCLUDED_DIRECTORIES = frozenset({".git", ".harness", "__pycache__"})
METADATA_FIELDS = ("document_date", "version", "status", "effective_from", "effective_to", "entity")
SCHEMA_VERSION = "1"
REGEX_TIMEOUT_SECONDS = 3.0


def _hash_file(path: Path) -> str:
    # Keep the streaming implementation usable independently of the CLI helpers.
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory(root: Path) -> Iterator[dict]:
    """Yield deterministic file records; symlinks are not followed."""
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError(f"corpus root is not a directory: {root}")
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIRECTORIES and not (Path(directory) / d).is_symlink())
        for name in sorted(files):
            path = Path(directory) / name
            if path.is_symlink() or not path.is_file():
                continue
            extension = path.suffix.lower()
            record = {"source_path": str(path), "relative_path": path.relative_to(root).as_posix(),
                      "format": extension.lstrip(".") or "unknown", "status": "supported" if extension in SUPPORTED_EXTENSIONS else "unsupported"}
            try:
                record.update(size_bytes=path.stat().st_size, source_hash=_hash_file(path))
            except OSError as exc:
                record.update(size_bytes=None, source_hash=None, status="error", error=str(exc))
            yield record


def _metadata(header: str, supplied: dict | None, relative_path: str) -> tuple[dict, dict]:
    values = dict.fromkeys(METADATA_FIELDS)
    origins = dict.fromkeys(METADATA_FIELDS)
    for line in header.splitlines()[:30]:
        key, sep, value = line.partition(":")
        key = key.strip().lower().replace("-", "_").replace(" ", "_")
        value = value.strip().strip("\"'")
        if sep and key in values and value:
            values[key], origins[key] = value, "header"
    supplied = supplied or {}
    overrides = {}
    # A manifest may use defaults + documents, a direct path mapping, or global fields.
    if isinstance(supplied.get("defaults"), dict):
        overrides.update(supplied["defaults"])
    overrides.update({key: supplied[key] for key in METADATA_FIELDS if key in supplied})
    documents = supplied.get("documents", supplied)
    if isinstance(documents, dict) and isinstance(documents.get(relative_path), dict):
        overrides.update(documents[relative_path])
    for key in METADATA_FIELDS:
        if key in overrides:
            value = overrides[key]
            if value is not None and not isinstance(value, (str, int, float, bool)):
                raise ValueError(f"metadata {relative_path}: {key} must be a scalar or null")
            values[key] = None if value is None else str(value)
            origins[key] = "provided"
    # Dates are explicit document metadata, never filesystem timestamps.
    for key in ("document_date", "effective_from", "effective_to"):
        if values[key]:
            try:
                if dt.date.fromisoformat(values[key]).isoformat() != values[key]:
                    raise ValueError()
            except ValueError as exc:
                raise ValueError(f"metadata {relative_path}: {key} must be YYYY-MM-DD") from exc
    return values, origins


def _schema(conn: sqlite3.Connection) -> bool:
    conn.executescript("""
        CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE documents (
            document_id TEXT PRIMARY KEY, source_path TEXT NOT NULL,
            relative_path TEXT NOT NULL UNIQUE, source_hash TEXT, size_bytes INTEGER,
            format TEXT NOT NULL, extraction_status TEXT NOT NULL,
            limitations TEXT NOT NULL, metadata TEXT NOT NULL, metadata_sources TEXT NOT NULL,
            document_date TEXT, version TEXT, status TEXT, effective_from TEXT,
            effective_to TEXT, entity TEXT);
        CREATE TABLE segments (id INTEGER PRIMARY KEY, evidence_id TEXT NOT NULL UNIQUE,
            document_id TEXT NOT NULL REFERENCES documents(document_id), ordinal INTEGER NOT NULL,
            locator TEXT NOT NULL, text TEXT NOT NULL, extraction_status TEXT NOT NULL,
            limitations TEXT NOT NULL);
        CREATE INDEX segments_document ON segments(document_id, ordinal);
        CREATE INDEX document_filters ON documents(status, document_date, entity);
    """)
    try:
        conn.execute("CREATE VIRTUAL TABLE segments_fts USING fts5(text, content='segments', content_rowid='id')")
    except sqlite3.OperationalError:
        return False
    return True


def index_corpus(root: Path, db_path: Path, metadata: dict | None = None, max_chars: int = 2_000_000) -> dict:
    """Atomically replace a complete index. A failed build preserves the old index.

    Extraction limitations, including text caps and missing optional parsers, are
    persisted and counted. Every run rebuilds the corpus, removing stale sources.
    """
    from .documents import iter_segments

    root, db_path = Path(root).resolve(), Path(db_path).resolve()
    if not root.is_dir():
        raise ValueError(f"corpus root is not a directory: {root}")
    if max_chars < 1:
        raise ValueError("max_chars must be positive")
    if metadata is not None and not isinstance(metadata, dict):
        raise ValueError("metadata must be an object")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{db_path.name}.", suffix=".building", dir=db_path.parent)
    os.close(handle)
    temporary_path = Path(temporary)
    counts = {key: 0 for key in ("ok", "partial", "unsupported", "error")}
    segment_count = 0
    try:
        with closing(sqlite3.connect(temporary_path)) as conn, conn:
            fts_available = _schema(conn)
            conn.executemany("INSERT INTO settings VALUES (?, ?)", [("schema_version", SCHEMA_VERSION), ("root", str(root)), ("fts_available", str(int(fts_available))), ("max_chars_per_document", str(max_chars))])
            for record in inventory(root):
                source = Path(record["source_path"])
                if source == db_path or str(source).startswith(str(temporary_path)) or str(source) in {str(db_path) + suffix for suffix in ("-wal", "-shm", "-journal")}:
                    continue
                relative = record["relative_path"]
                document_id = "doc-" + hashlib.sha256(relative.encode()).hexdigest()[:24]
                limitations = []
                extraction_status = "ok"
                header_parts = []
                header_length = 0
                conn.execute("INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                    document_id, record["source_path"], relative, record["source_hash"], record["size_bytes"], record["format"], "ok", "[]", "{}", "{}", *([None] * 6)))
                try:
                    if record["status"] == "error":
                        raise OSError(record["error"])
                    for ordinal, segment in enumerate(iter_segments(source, max_chars=max_chars)):
                        text = segment.get("text", "")
                        state = segment.get("extraction_status", "ok")
                        if state not in counts:
                            raise ValueError(f"invalid extraction status: {state}")
                        if {"ok": 0, "partial": 1, "unsupported": 2, "error": 3}[state] > {"ok": 0, "partial": 1, "unsupported": 2, "error": 3}[extraction_status]:
                            extraction_status = state
                        limitations.extend(segment.get("limitations", []))
                        if not text:
                            continue
                        if header_length < 12_000:
                            header_parts.append(text[:12_000 - header_length])
                            header_length += len(text)
                        locator_json = json.dumps(segment["locator"], ensure_ascii=False, sort_keys=True)
                        evidence_id = "ev-" + hashlib.sha256((document_id + str(record["source_hash"]) + locator_json).encode()).hexdigest()[:32]
                        conn.execute("INSERT INTO segments(evidence_id,document_id,ordinal,locator,text,extraction_status,limitations) VALUES (?,?,?,?,?,?,?)", (
                            evidence_id, document_id, ordinal, locator_json, text, state, json.dumps(segment.get("limitations", []), ensure_ascii=False)))
                        segment_count += 1
                except (OSError, ValueError, UnicodeError) as exc:
                    extraction_status = "error"
                    limitations.append(str(exc))
                # Detect a source modified during indexing instead of claiming its old hash.
                try:
                    if record["source_hash"] and _hash_file(source) != record["source_hash"]:
                        raise ValueError(f"source changed during indexing: {source}")
                except OSError as exc:
                    raise ValueError(f"source unavailable after indexing: {source}") from exc
                values, origins = _metadata("\n".join(header_parts), metadata, relative)
                limitations = list(dict.fromkeys(limitations))
                conn.execute("UPDATE documents SET extraction_status=?,limitations=?,metadata=?,metadata_sources=?,document_date=?,version=?,status=?,effective_from=?,effective_to=?,entity=? WHERE document_id=?", (
                    extraction_status, json.dumps(limitations, ensure_ascii=False), json.dumps(values, ensure_ascii=False), json.dumps(origins), *(values[key] for key in METADATA_FIELDS), document_id))
                counts[extraction_status] += 1
            if fts_available:
                conn.execute("INSERT INTO segments_fts(segments_fts) VALUES ('rebuild')")
            conn.commit()
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise ValueError(f"index integrity check failed: {integrity}")
        os.replace(temporary_path, db_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return {"database": str(db_path), "root": str(root), "document_count": sum(counts.values()), "segment_count": segment_count,
            "extraction_status_counts": counts, "fts_available": fts_available, "complete": not any(counts[key] for key in ("partial", "unsupported", "error")), "max_chars_per_document": max_chars}


def _readonly(db_path: Path) -> sqlite3.Connection:
    if not Path(db_path).is_file():
        raise ValueError(f"index does not exist: {db_path}")
    conn = sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        version = conn.execute("SELECT value FROM settings WHERE key='schema_version'").fetchone()
        if version is None or version[0] != SCHEMA_VERSION:
            raise ValueError("unsupported corpus index schema")
    except Exception:
        conn.close()
        raise
    return conn


def _search(db_path: Path, query: str, *, mode: str, limit: int, max_chars: int, status: str | None,
            date_from: str | None, date_to: str | None, entity: str | None) -> dict:
    conn = _readonly(db_path)
    try:
        conditions, parameters = [], []
        for field, value, operator in (("status", status, "="), ("document_date", date_from, ">="), ("document_date", date_to, "<="), ("entity", entity, "=")):
            if value is not None:
                conditions.append(f"d.{field} {operator} ?")
                parameters.append(value)
        join = ""
        if mode == "fts":
            available = conn.execute("SELECT value FROM settings WHERE key='fts_available'").fetchone()
            if not available or available[0] != "1":
                raise ValueError("FTS5 is unavailable; use literal or regex search")
            join = " JOIN segments_fts ON segments_fts.rowid=s.id"
            conditions.append("segments_fts MATCH ?")
            parameters.append(query)
        elif mode == "literal":
            conditions.append("instr(s.text, ?) > 0")
            parameters.append(query)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        order = "bm25(segments_fts), d.relative_path, s.ordinal" if mode == "fts" else "d.relative_path, s.ordinal"
        highlight = ",highlight(segments_fts,0,'__CORPUS_MATCH_START__','__CORPUS_MATCH_END__') AS highlighted" if mode == "fts" else ""
        sql = "SELECT s.*" + highlight + ",d.source_path,d.relative_path,d.source_hash,d.metadata,d.metadata_sources,d.extraction_status AS document_extraction_status,d.limitations AS document_limitations FROM segments s JOIN documents d ON d.document_id=s.document_id" + join + where + " ORDER BY " + order
        expression = re.compile(query) if mode == "regex" else None
        results = []
        truncated = False
        for row in conn.execute(sql, parameters):
            text = row["text"]
            match = expression.search(text) if expression is not None else None
            if expression is not None and match is None:
                continue
            if len(results) >= limit:
                truncated = True
                break
            match_start = match.start() if match is not None else text.find(query) if mode == "literal" else 0
            if mode == "fts":
                highlighted = row["highlighted"]
                position = highlighted.find("__CORPUS_MATCH_START__")
                if position >= 0 and highlighted[:position] == text[:position]:
                    match_start = position
            match_end = match.end() if match is not None else match_start + len(query) if mode == "literal" else 0
            start = max(0, match_start - max_chars // 3)
            start = min(start, max(0, len(text) - max_chars))
            end = min(len(text), start + max_chars)
            results.append({"document_id": row["document_id"], "source_path": row["source_path"], "relative_path": row["relative_path"], "source_hash": row["source_hash"],
                            "evidence_id": row["evidence_id"], "locator": json.loads(row["locator"]), "excerpt": text[start:end],
                            "excerpt_start": start, "excerpt_end": end, "match_start": match_start, "match_end": match_end,
                            "metadata": json.loads(row["metadata"]), "metadata_sources": json.loads(row["metadata_sources"]),
                            "extraction_status": row["document_extraction_status"],
                            "limitations": list(dict.fromkeys(json.loads(row["document_limitations"]) + json.loads(row["limitations"])))})
        extraction_cap = int(conn.execute("SELECT value FROM settings WHERE key='max_chars_per_document'").fetchone()[0])
        incomplete = conn.execute("SELECT count(*) FROM documents WHERE extraction_status != 'ok'").fetchone()[0]
        return {"max_chars_per_document": extraction_cap, "corpus_complete": incomplete == 0, "incomplete_documents": incomplete, "database": str(Path(db_path).resolve()), "query": query, "mode": mode, "results": results, "result_count": len(results), "truncated": truncated,
                "filters": {"status": status, "date_from": date_from, "date_to": date_to, "entity": entity},
                "limitations": ["Matches cannot cross extraction segment boundaries."]}
    except (sqlite3.Error, re.error) as exc:
        raise ValueError(f"invalid {mode} search or corpus index: {exc}") from exc
    finally:
        conn.close()


def _regex_worker(connection, db_path, query, options):
    try:
        connection.send((True, _search(db_path, query, mode="regex", **options)))
    except Exception as exc:
        connection.send((False, str(exc)))
    finally:
        connection.close()


def search(db_path: Path, query: str, *, mode: str = "literal", limit: int = 20, max_chars: int = 600,
           status: str | None = None, date_from: str | None = None, date_to: str | None = None,
           entity: str | None = None) -> dict:
    """Search exact literals, bounded regex, or raw SQLite FTS5 queries.

    Returned excerpts are exact slices of the original extraction segments. Date
    filters are inclusive and use explicit document_date metadata only. Regex
    searches exceeding three seconds are terminated and raise ValueError.
    """
    if mode not in {"literal", "regex", "fts"}:
        raise ValueError("mode must be literal, regex, or fts")
    if not isinstance(query, str) or not query:
        raise ValueError("query must be a nonempty string")
    if mode == "regex" and len(query) > 512:
        raise ValueError("regex query is limited to 512 characters")
    if not 1 <= limit <= 1000 or not 1 <= max_chars <= 10_000:
        raise ValueError("limit must be 1..1000 and max_chars must be 1..10000")
    for name, value in (("date_from", date_from), ("date_to", date_to)):
        if value is not None:
            try:
                if dt.date.fromisoformat(value).isoformat() != value:
                    raise ValueError()
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{name} must be YYYY-MM-DD") from exc
    if date_from and date_to and date_from > date_to:
        raise ValueError("date_from must not exceed date_to")
    options = dict(limit=limit, max_chars=max_chars, status=status, date_from=date_from, date_to=date_to, entity=entity)
    if mode != "regex":
        return _search(db_path, query, mode=mode, **options)
    receiver, sender = multiprocessing.Pipe(duplex=False)
    process = multiprocessing.Process(target=_regex_worker, args=(sender, db_path, query, options), daemon=True)
    try:
        process.start()
        sender.close()
        if not receiver.poll(REGEX_TIMEOUT_SECONDS):
            raise ValueError(f"regex search exceeded {REGEX_TIMEOUT_SECONDS:g} second time limit")
        try:
            success, value = receiver.recv()
        except EOFError as exc:
            raise ValueError("regex search worker exited without a result") from exc
        if not success:
            raise ValueError(value)
        return value
    finally:
        if process.pid is not None:
            if process.is_alive():
                process.terminate()
            process.join()
        receiver.close()
        sender.close()
