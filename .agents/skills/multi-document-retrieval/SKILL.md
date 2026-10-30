---
name: multi-document-retrieval
description: "Find information across many local files using bounded inventory, extraction and search; use for corpus exploration or building a small Evidence Pack."
---
# Multi Document Retrieval

Original project and exam rules take precedence. No Astra, external transfers, computer/browser automation, CLI updates or exam push.

**Inputs:** Corpus directory, identifiers/questions, approved local output paths, size budget.
**Procedure:**
1. Run `python3 -m harness resources` and `corpus inventory ROOT`; preserve originals and locate relevant formats.
2. Run `corpus index ROOT --db LOCAL.db`, inspect extraction statuses and caps. Do not call scans or missing parser output successful.
3. Use `corpus search --db LOCAL.db --query ID --mode literal`; Korean substrings and identifiers use literal; use regex or available FTS5 for appropriate queries. Refine dates/status/entity; latest draft is not automatically effective.
4. Build `corpus evidence-pack --db LOCAL.db --query ID --query EXCEPTION-ID --max-evidence 12 --max-chars 16000 --output PACK.json`. Expand uncovered queries rather than asserting absence.
   Check `truncated` even when `uncovered_queries` is empty. A hit per query does not cover all matching documents. Increase limits or independently rebuild a narrower, explicit scope before a definitive conclusion.
**Output contract:** Source paths/hashes, actual locators, selected citation IDs, coverage and extraction limits, bounded local pack.
**Tools:** Existing corpus CLI, SQLite FTS5 when available; no embeddings, uploads or browser automation.
**Verification:** Search middle/end of representative files, check pack coverage/size and run `evidence verify PACK.json`.
**Failure handling:** Report unsupported formats, incomplete indexing, regex timeout or missing matches. Re-index with an explicit larger cap or narrowed source scope; never invent OCR or locations.
**Relationships:** document-processing handles format fidelity; data-processing handles row computations; cross-document-synthesis consumes the pack.
Read [references/retrieval.md](references/retrieval.md) for CLI and locator caveats.
