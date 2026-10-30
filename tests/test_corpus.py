"""Synthetic corpus integration tests; no work documents or external services."""
from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from harness.corpus import index_corpus, inventory, search


class CorpusTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "sources"
        self.root.mkdir()
        self.db = Path(self.temporary.name) / "corpus.sqlite"

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_inventory_hash_exclusions_and_unsupported(self):
        source = self.write("policy.md", "합성 규정 ABC-102")
        self.write(".git/private.txt", "ignored")
        self.write(".harness/evidence.txt", "ignored")
        self.write("__pycache__/ignored.txt", "ignored")
        self.write("legacy.hwp", "unsupported")
        (self.root / "link.md").symlink_to(source)
        rows = list(inventory(self.root))
        self.assertEqual([r["relative_path"] for r in rows], ["legacy.hwp", "policy.md"])
        self.assertEqual(rows[1]["source_hash"], hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertEqual(rows[0]["status"], "unsupported")

    def test_middle_end_korean_identifiers_and_exact_slices(self):
        content = "start\n" + "irrelevant text\n" * 1300 + "중간검증 ABC-102\n" + "other text\n" * 1400 + "끝검증 END-981\n"
        self.write("long.txt", content)
        report = index_corpus(self.root, self.db)
        self.assertEqual(report["document_count"], 1)
        self.assertGreater(report["segment_count"], 2)
        for query in ("중간검증", "ABC-102", "끝검증", "END-981"):
            found = search(self.db, query, max_chars=80)
            self.assertTrue(found["results"], query)
            row = found["results"][0]
            self.assertIn(query, row["excerpt"])
            self.assertIn(row["excerpt"], content)
            self.assertLessEqual(len(row["excerpt"]), 80)
            self.assertTrue(row["evidence_id"].startswith("ev-"))
            self.assertEqual(found["max_chars_per_document"], 2_000_000)

    def test_explicit_metadata_filters_and_stable_identity(self):
        self.write("a.md", "---\ndocument_date: 2026-01-05\nstatus: draft\nversion: v2\nentity: Team A\n---\n승인 승인번호 APP-44")
        self.write("b.txt", "document_date: 2025-12-31\nstatus: final\nentity: Team B\n승인 APP-55")
        metadata = {"documents": {"a.md": {"status": "final", "effective_from": "2026-02-01"}}}
        index_corpus(self.root, self.db, metadata)
        first = search(self.db, "승인", status="final", date_from="2026-01-01", date_to="2026-12-31", entity="Team A")["results"]
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0]["metadata"]["version"], "v2")
        self.assertEqual(first[0]["metadata_sources"]["document_date"], "header")
        self.assertEqual(first[0]["metadata_sources"]["status"], "provided")
        index_corpus(self.root, self.db, metadata)
        second = search(self.db, "APP-44")["results"][0]
        self.assertEqual(first[0]["document_id"], second["document_id"])
        self.assertEqual(first[0]["evidence_id"], second["evidence_id"])
        self.assertEqual(search(self.db, "승인", entity="missing")["results"], [])

    def test_cap_unsupported_and_empty_status_records(self):
        self.write("limited.txt", "x" * 100 + "middle" + "x" * 100 + "tail")
        self.write("unsupported.bin", "opaque")
        report = index_corpus(self.root, self.db, max_chars=80)
        self.assertEqual(report["extraction_status_counts"]["partial"], 1)
        self.assertEqual(report["extraction_status_counts"]["unsupported"], 1)
        self.assertFalse(report["complete"])
        self.assertFalse(search(self.db, "tail")["results"])
        row = search(self.db, "xxx")["results"][0]
        self.assertEqual(row["extraction_status"], "partial")
        self.assertTrue(row["limitations"])
        self.assertEqual(search(self.db, "xxx")["max_chars_per_document"], 80)

    def test_regex_fts_validation_and_limits(self):
        self.write("a.txt", "ABC-441 and alpha\n" + "plain " * 400 + "needleword\n")
        self.write("b.txt", "ABC-442 and alpha")
        report = index_corpus(self.root, self.db)
        result = search(self.db, r"ABC-\d{3}", mode="regex", limit=1)
        self.assertEqual(len(result["results"]), 1)
        self.assertTrue(result["truncated"])
        self.assertIn("ABC-441", result["results"][0]["excerpt"])
        with self.assertRaisesRegex(ValueError, "regex"):
            search(self.db, "[", mode="regex")
        if report["fts_available"]:
            self.assertIn("needleword", search(self.db, "needleword", mode="fts", max_chars=50)["results"][0]["excerpt"])
            with self.assertRaisesRegex(ValueError, "fts"):
                search(self.db, '"unterminated', mode="fts")
        for kwargs in ({"limit": 0}, {"max_chars": 0}, {"mode": "unknown"}, {"date_from": "yesterday"}):
            with self.assertRaises(ValueError):
                search(self.db, "alpha", **kwargs)
        with self.assertRaises(ValueError):
            search(self.db, "")

    def test_catastrophic_regex_is_terminated(self):
        self.write("a.txt", "a" * 3500 + "!")
        index_corpus(self.root, self.db)
        with patch("harness.corpus.REGEX_TIMEOUT_SECONDS", 0.1):
            with self.assertRaisesRegex(ValueError, "time limit"):
                search(self.db, "(a+)+$", mode="regex")

    def test_atomic_rebuild_preserves_previous_on_failure_and_removes_stale(self):
        source = self.write("old.txt", "old content")
        index_corpus(self.root, self.db)
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            index_corpus(self.root, self.db, {"document_date": "invalid"})
        self.assertTrue(search(self.db, "old content")["results"])
        source.unlink()
        self.write("new.txt", "new content")
        index_corpus(self.root, self.db)
        self.assertFalse(search(self.db, "old content")["results"])
        self.assertTrue(search(self.db, "new content")["results"])
        self.assertEqual(list(self.db.parent.glob(".*.building*")), [])

    def test_database_inside_root_is_not_indexed(self):
        self.write("a.txt", "content")
        inside = self.root / "index.sqlite"
        self.assertEqual(index_corpus(self.root, inside)["document_count"], 1)
        self.assertEqual(index_corpus(self.root, inside)["document_count"], 1)
        with closing(sqlite3.connect(inside)) as conn:
            self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")

    def test_no_filesystem_date_inference(self):
        self.write("a.txt", "no metadata keyword")
        index_corpus(self.root, self.db)
        row = search(self.db, "keyword")["results"][0]
        self.assertIsNone(row["metadata"]["document_date"])
        self.assertEqual(search(self.db, "keyword", date_from="2000-01-01")["results"], [])

    def test_identifier_boundaries_avoid_numeric_distractors(self):
        self.write('a.txt','BASE-420 XBASE-42 BASE-42-OLD\ncorrect: BASE-42\n')
        index_corpus(self.root,self.db)
        result=search(self.db,'BASE-42',mode='identifier')
        self.assertEqual(result['result_count'],1)
        self.assertIn('correct',result['results'][0]['excerpt'])


if __name__ == "__main__":
    unittest.main()
