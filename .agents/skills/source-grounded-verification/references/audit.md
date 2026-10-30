# Audit boundaries
`evidence verify` rehashes each source, extracts the exact original locator and checks the excerpt offsets. Different slices of one segment have distinct citation_id values. It rejects nonexistent paths/locators and changed hashes. It does not authenticate the author, confirm legal approval, verify arbitrary prose conclusions, or certify a user-supplied metadata manifest. DOCX/JSON/CSV text is parser-rendered content, not a byte-for-byte serialization of the original container; retain locators and limitations.

Synthesis also rechecks status/date metadata against original extracted headers. Differing manifest overrides need independent validation. Partial, unsupported, failed or capped extraction cannot silently support a complete conclusion. PDF OCR and table reading order remain unresolved unless separately checked. XLSX cached formulas are not recalculated.

Report severity, original location, candidate claim, expected/observed, exact command and scope. When computation differs, return both values/units and relevant inclusion/exclusion counts. Do not equate a verified quotation with a verified business interpretation.
